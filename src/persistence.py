"""File-based persistence for session backup and recovery."""

import json
import pickle
import gzip
import hashlib
import time
import threading
from typing import Dict, List, Any, Optional, Tuple
from pathlib import Path
from datetime import datetime, timezone
from dataclasses import dataclass, asdict
from .memory_manager import MemoryManager, ConversationSession
from .config import Config
import logging


@dataclass
class BackupMetadata:
    """Metadata for backup files."""
    version: str
    created_at: str
    session_count: int
    total_messages: int
    total_tokens: int
    backup_type: str
    compression: bool
    checksum: str


class SessionPersistence:
    """Handles file-based persistence for conversation sessions."""
    
    def __init__(self, backup_dir: str = None):
        self.backup_dir = Path(backup_dir or Path.home() / ".chat_client" / "backups")
        self.backup_dir.mkdir(parents=True, exist_ok=True)
        
        self.auto_save_enabled = True
        self.auto_save_interval = Config.AUTO_SAVE_INTERVAL
        self.compression_enabled = True
        self.max_backups = 10
        
        self.logger = logging.getLogger(__name__)
        self._last_auto_save = time.time()
        self._auto_save_thread = None
        self._shutdown_event = threading.Event()
        
        # Start auto-save if enabled
        if self.auto_save_enabled:
            self._start_auto_save_thread()
    
    def save_sessions(self, memory_manager: MemoryManager, backup_name: str = None) -> str:
        """Save all sessions to a backup file."""
        if backup_name is None:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            backup_name = f"session_backup_{timestamp}"
        
        backup_data = self._prepare_backup_data(memory_manager)
        backup_file = self._write_backup_file(backup_data, backup_name)
        
        self.logger.info(f"Saved {len(memory_manager.sessions)} sessions to {backup_file}")
        return str(backup_file)
    
    def load_sessions(self, backup_file: str) -> Tuple[Dict[str, ConversationSession], Optional[str]]:
        """Load sessions from a backup file."""
        backup_path = Path(backup_file)
        if not backup_path.exists():
            # Try looking in backup directory
            backup_path = self.backup_dir / backup_file
            if not backup_path.exists():
                raise FileNotFoundError(f"Backup file not found: {backup_file}")
        
        backup_data = self._read_backup_file(backup_path)
        sessions, current_session_id = self._restore_sessions_from_data(backup_data)
        
        self.logger.info(f"Loaded {len(sessions)} sessions from {backup_path}")
        return sessions, current_session_id
    
    def list_backups(self) -> List[Dict[str, Any]]:
        """List all available backup files."""
        backups = []
        
        for backup_file in self.backup_dir.glob("*.backup*"):
            try:
                metadata = self._read_backup_metadata(backup_file)
                file_stats = backup_file.stat()
                
                backups.append({
                    "filename": backup_file.name,
                    "full_path": str(backup_file),
                    "created_at": metadata.created_at,
                    "session_count": metadata.session_count,
                    "total_messages": metadata.total_messages,
                    "file_size": file_stats.st_size,
                    "backup_type": metadata.backup_type,
                    "compressed": metadata.compression
                })
            except Exception as e:
                self.logger.warning(f"Could not read backup metadata for {backup_file}: {e}")
        
        # Sort by creation time (newest first)
        backups.sort(key=lambda x: x["created_at"], reverse=True)
        return backups
    
    def delete_backup(self, backup_file: str) -> bool:
        """Delete a backup file."""
        backup_path = Path(backup_file)
        if not backup_path.exists():
            backup_path = self.backup_dir / backup_file
        
        try:
            backup_path.unlink()
            self.logger.info(f"Deleted backup: {backup_path}")
            return True
        except Exception as e:
            self.logger.error(f"Failed to delete backup {backup_path}: {e}")
            return False
    
    def cleanup_old_backups(self) -> int:
        """Remove old backup files beyond the maximum limit."""
        backups = self.list_backups()
        
        if len(backups) <= self.max_backups:
            return 0
        
        # Keep the most recent backups
        backups_to_delete = backups[self.max_backups:]
        deleted_count = 0
        
        for backup in backups_to_delete:
            if self.delete_backup(backup["full_path"]):
                deleted_count += 1
        
        self.logger.info(f"Cleaned up {deleted_count} old backup files")
        return deleted_count
    
    def auto_save(self, memory_manager: MemoryManager) -> bool:
        """Perform automatic save if conditions are met."""
        current_time = time.time()
        
        if current_time - self._last_auto_save < self.auto_save_interval:
            return False
        
        # Only auto-save if there are sessions with content
        if not memory_manager.sessions or all(len(session.messages) == 0 for session in memory_manager.sessions.values()):
            return False
        
        try:
            backup_file = self.save_sessions(memory_manager, "auto_save")
            self._last_auto_save = current_time
            self.logger.debug("Auto-save completed successfully")
            return True
        except Exception as e:
            self.logger.error(f"Auto-save failed: {e}")
            return False
    
    def _prepare_backup_data(self, memory_manager: MemoryManager) -> Dict[str, Any]:
        """Prepare session data for backup."""
        sessions_data = {}
        total_messages = 0
        total_tokens = 0
        
        for session_id, session in memory_manager.sessions.items():
            sessions_data[session_id] = session.export_data()
            total_messages += len(session.messages)
            total_tokens += session.metadata.total_tokens
        
        # Create metadata
        metadata = BackupMetadata(
            version="1.0",
            created_at=datetime.now(timezone.utc).isoformat(),
            session_count=len(memory_manager.sessions),
            total_messages=total_messages,
            total_tokens=total_tokens,
            backup_type="full",
            compression=self.compression_enabled,
            checksum=""  # Will be calculated later
        )
        
        backup_data = {
            "metadata": asdict(metadata),
            "current_session_id": memory_manager.current_session_id,
            "sessions": sessions_data,
            "format_version": "1.0",
            "created_by": "Claude Chat Client"
        }
        
        # Calculate checksum
        data_for_checksum = json.dumps(backup_data, sort_keys=True)
        checksum = hashlib.sha256(data_for_checksum.encode()).hexdigest()
        backup_data["metadata"]["checksum"] = checksum
        
        return backup_data
    
    def _write_backup_file(self, backup_data: Dict[str, Any], backup_name: str) -> Path:
        """Write backup data to file."""
        if self.compression_enabled:
            backup_file = self.backup_dir / f"{backup_name}.backup.gz"
            with gzip.open(backup_file, 'wt', encoding='utf-8') as f:
                json.dump(backup_data, f, indent=2)
        else:
            backup_file = self.backup_dir / f"{backup_name}.backup.json"
            with open(backup_file, 'w', encoding='utf-8') as f:
                json.dump(backup_data, f, indent=2)
        
        return backup_file
    
    def _read_backup_file(self, backup_path: Path) -> Dict[str, Any]:
        """Read backup data from file."""
        try:
            if backup_path.suffix == '.gz':
                with gzip.open(backup_path, 'rt', encoding='utf-8') as f:
                    backup_data = json.load(f)
            else:
                with open(backup_path, 'r', encoding='utf-8') as f:
                    backup_data = json.load(f)
            
            # Verify checksum if present
            if "metadata" in backup_data and "checksum" in backup_data["metadata"]:
                stored_checksum = backup_data["metadata"]["checksum"]
                backup_data["metadata"]["checksum"] = ""  # Remove for verification
                
                data_for_checksum = json.dumps(backup_data, sort_keys=True)
                calculated_checksum = hashlib.sha256(data_for_checksum.encode()).hexdigest()
                
                if stored_checksum != calculated_checksum:
                    self.logger.warning(f"Checksum mismatch in backup file {backup_path}")
                
                backup_data["metadata"]["checksum"] = stored_checksum
            
            return backup_data
            
        except Exception as e:
            self.logger.error(f"Failed to read backup file {backup_path}: {e}")
            raise
    
    def _read_backup_metadata(self, backup_path: Path) -> BackupMetadata:
        """Read only metadata from backup file."""
        if backup_path.suffix == '.gz':
            with gzip.open(backup_path, 'rt', encoding='utf-8') as f:
                # Read just enough to get metadata
                content = f.read(1024)  # Should be enough for metadata
                
        else:
            with open(backup_path, 'r', encoding='utf-8') as f:
                content = f.read(1024)
        
        # Parse partial JSON to get metadata
        try:
            # Find metadata section
            import re
            metadata_match = re.search(r'"metadata":\s*({[^}]*})', content)
            if metadata_match:
                metadata_json = metadata_match.group(1)
                metadata_dict = json.loads(metadata_json)
                return BackupMetadata(**metadata_dict)
        except:
            pass
        
        # Fallback: read full file
        backup_data = self._read_backup_file(backup_path)
        return BackupMetadata(**backup_data["metadata"])
    
    def _restore_sessions_from_data(self, backup_data: Dict[str, Any]) -> Tuple[Dict[str, ConversationSession], Optional[str]]:
        """Restore sessions from backup data."""
        sessions = {}
        
        for session_id, session_data in backup_data["sessions"].items():
            session = ConversationSession.from_export_data(session_data)
            sessions[session_id] = session
        
        current_session_id = backup_data.get("current_session_id")
        
        return sessions, current_session_id
    
    def _start_auto_save_thread(self):
        """Start the auto-save background thread."""
        if self._auto_save_thread and self._auto_save_thread.is_alive():
            return
        
        self._shutdown_event.clear()
        self._auto_save_thread = threading.Thread(target=self._auto_save_worker, daemon=True)
        self._auto_save_thread.start()
        self.logger.info("Auto-save thread started")
    
    def _auto_save_worker(self):
        """Background worker for auto-save."""
        while not self._shutdown_event.is_set():
            try:
                # Wait for the interval or shutdown signal
                if self._shutdown_event.wait(timeout=self.auto_save_interval):
                    break  # Shutdown requested
                
                # Auto-save would be triggered by the memory manager
                # This is just the scheduling thread
                
            except Exception as e:
                self.logger.error(f"Error in auto-save worker: {e}")
                # Continue running despite errors
    
    def shutdown(self):
        """Shutdown the persistence system."""
        self.logger.info("Shutting down persistence system")
        
        # Stop auto-save thread
        if self._auto_save_thread:
            self._shutdown_event.set()
            self._auto_save_thread.join(timeout=5)
        
        # Clean up old backups
        try:
            self.cleanup_old_backups()
        except Exception as e:
            self.logger.warning(f"Error during backup cleanup: {e}")


class SessionImportExport:
    """Utilities for importing/exporting sessions in various formats."""
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
    
    def export_to_json(self, session: ConversationSession, file_path: str) -> bool:
        """Export a single session to JSON format."""
        try:
            export_data = {
                "session_info": {
                    "name": session.name,
                    "session_id": session.session_id,
                    "created_at": session.metadata.created_at,
                    "message_count": len(session.messages),
                    "total_tokens": session.metadata.total_tokens,
                    "exported_at": datetime.now(timezone.utc).isoformat()
                },
                "messages": [
                    {
                        "role": msg.role,
                        "content": msg.content,
                        "timestamp": msg.timestamp,
                        "tokens": msg.tokens,
                        "metadata": msg.metadata or {}
                    }
                    for msg in session.messages
                ],
                "pinned_messages": session.pinned_messages
            }
            
            with open(file_path, 'w', encoding='utf-8') as f:
                json.dump(export_data, f, indent=2, ensure_ascii=False)
            
            self.logger.info(f"Exported session '{session.name}' to {file_path}")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to export session to JSON: {e}")
            return False
    
    def import_from_json(self, file_path: str) -> Optional[ConversationSession]:
        """Import a session from JSON format."""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                import_data = json.load(f)
            
            # Extract session info
            session_info = import_data.get("session_info", {})
            session_id = session_info.get("session_id", "imported_session")
            session_name = session_info.get("name", "Imported Session")
            
            # Create session
            session = ConversationSession(session_id, session_name)
            
            # Import messages
            for msg_data in import_data.get("messages", []):
                session.add_message(
                    role=msg_data["role"],
                    content=msg_data["content"],
                    tokens=msg_data.get("tokens", 0),
                    metadata=msg_data.get("metadata", {})
                )
                
                # Set timestamp if available
                if "timestamp" in msg_data and session.messages:
                    session.messages[-1].timestamp = msg_data["timestamp"]
            
            # Import pinned messages
            session.pinned_messages = import_data.get("pinned_messages", [])
            
            self.logger.info(f"Imported session '{session_name}' from {file_path}")
            return session
            
        except Exception as e:
            self.logger.error(f"Failed to import session from JSON: {e}")
            return None
    
    def export_to_markdown(self, session: ConversationSession, file_path: str) -> bool:
        """Export a session to Markdown format."""
        try:
            lines = [
                f"# Chat Session: {session.name}",
                "",
                f"**Session ID:** {session.session_id}",
                f"**Created:** {session.metadata.created_at}",
                f"**Messages:** {len(session.messages)}",
                f"**Total Tokens:** {session.metadata.total_tokens}",
                f"**Exported:** {datetime.now(timezone.utc).isoformat()}",
                "",
                "---",
                ""
            ]
            
            for i, message in enumerate(session.messages):
                role_display = "🧑 **You**" if message.role == "user" else "🤖 **Claude**"
                
                # Format timestamp
                try:
                    timestamp = datetime.fromisoformat(message.timestamp.replace('Z', '+00:00'))
                    time_display = timestamp.strftime('%H:%M:%S')
                except:
                    time_display = "Unknown"
                
                lines.append(f"## {role_display} [{time_display}]")
                lines.append("")
                
                if message.role == "system":
                    lines.append(f"*System: {message.content}*")
                else:
                    # Handle code blocks in content
                    content = message.content
                    if "```" in content:
                        # Already formatted code blocks
                        lines.append(content)
                    else:
                        lines.append(content)
                
                if i in session.pinned_messages:
                    lines.append("")
                    lines.append("📌 *Pinned Message*")
                
                lines.append("")
                lines.append("---")
                lines.append("")
            
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write("\n".join(lines))
            
            self.logger.info(f"Exported session '{session.name}' to Markdown: {file_path}")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to export session to Markdown: {e}")
            return False
    
    def export_to_text(self, session: ConversationSession, file_path: str) -> bool:
        """Export a session to plain text format."""
        try:
            lines = [
                f"Chat Session: {session.name}",
                f"Session ID: {session.session_id}",
                f"Created: {session.metadata.created_at}",
                f"Messages: {len(session.messages)}",
                f"Total Tokens: {session.metadata.total_tokens}",
                f"Exported: {datetime.now(timezone.utc).isoformat()}",
                "",
                "=" * 80,
                ""
            ]
            
            for i, message in enumerate(session.messages):
                role_display = "You" if message.role == "user" else "Claude"
                
                try:
                    timestamp = datetime.fromisoformat(message.timestamp.replace('Z', '+00:00'))
                    time_display = timestamp.strftime('%H:%M:%S')
                except:
                    time_display = "Unknown"
                
                lines.append(f"[{time_display}] {role_display}:")
                lines.append(message.content)
                
                if i in session.pinned_messages:
                    lines.append("(Pinned)")
                
                lines.append("")
                lines.append("-" * 40)
                lines.append("")
            
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write("\n".join(lines))
            
            self.logger.info(f"Exported session '{session.name}' to text: {file_path}")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to export session to text: {e}")
            return False


class PersistentMemoryManager(MemoryManager):
    """Memory manager with built-in persistence capabilities."""
    
    def __init__(self, persistence: SessionPersistence = None):
        super().__init__()
        self.persistence = persistence or SessionPersistence()
        self.auto_backup_enabled = True
        self.import_export = SessionImportExport()
    
    def save_to_file(self, backup_name: str = None) -> str:
        """Save all sessions to a backup file."""
        return self.persistence.save_sessions(self, backup_name)
    
    def load_from_file(self, backup_file: str) -> bool:
        """Load sessions from a backup file."""
        try:
            sessions, current_session_id = self.persistence.load_sessions(backup_file)
            
            # Replace current sessions
            self.sessions = sessions
            self.current_session_id = current_session_id
            
            # Validate current session
            if self.current_session_id and self.current_session_id not in self.sessions:
                # Set first session as current if original current session is missing
                if self.sessions:
                    self.current_session_id = next(iter(self.sessions.keys()))
                else:
                    self.current_session_id = None
            
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to load sessions from file: {e}")
            return False
    
    def add_message(self, role: str, content: str, tokens: int = 0, metadata: Dict[str, Any] = None) -> bool:
        """Add message with automatic backup if enabled."""
        result = super().add_message(role, content, tokens, metadata)
        
        if result and self.auto_backup_enabled:
            self.persistence.auto_save(self)
        
        return result
    
    def list_backups(self) -> List[Dict[str, Any]]:
        """List all available backup files."""
        return self.persistence.list_backups()
    
    def export_session_to_file(self, session_id: str, file_path: str, format_type: str = "json") -> bool:
        """Export a specific session to file."""
        if session_id not in self.sessions:
            return False
        
        session = self.sessions[session_id]
        
        if format_type.lower() == "json":
            return self.import_export.export_to_json(session, file_path)
        elif format_type.lower() == "markdown":
            return self.import_export.export_to_markdown(session, file_path)
        elif format_type.lower() == "txt":
            return self.import_export.export_to_text(session, file_path)
        else:
            self.logger.error(f"Unsupported export format: {format_type}")
            return False
    
    def import_session_from_file(self, file_path: str) -> Optional[str]:
        """Import a session from file."""
        session = self.import_export.import_from_json(file_path)
        if session:
            # Ensure unique session ID
            original_id = session.session_id
            counter = 1
            while session.session_id in self.sessions:
                session.session_id = f"{original_id}_{counter}"
                counter += 1
            
            self.sessions[session.session_id] = session
            return session.session_id
        
        return None
    
    def shutdown(self):
        """Shutdown with final backup."""
        if self.auto_backup_enabled and self.sessions:
            try:
                self.persistence.save_sessions(self, "final_backup")
            except Exception as e:
                self.logger.warning(f"Final backup failed: {e}")
        
        self.persistence.shutdown()