import logging
import os
import socket

import paramiko


class SSHComms:
    """Thin wrapper around paramiko SSHClient with simple exec and SFTP helpers.

    Usage:
        ssh = SSHComms(host)
        ssh.open_with_key(<key_path>)  # or open_with_password('password')
        ok, out = ssh.exec('uptime')
        ssh.close()
    """

    def __init__(self, host: str, *, username: str = 'root', password: str | None = None,
                 key_path: str | os.PathLike | None = None, timeout: float = 30.0) -> None:
        self.host = host
        self.username = username
        self.password = password
        self.key_path = str(key_path) if key_path is not None else None
        self.timeout = timeout
        self._client: paramiko.SSHClient | None = None

    # Context manager support
    def __enter__(self):
        self.open()
        return self

    def __exit__(self, exc_type, exc, tb):
        self.close()
        return False

    # --- connection management -------------------------------------------------
    def _ensure_client(self) -> paramiko.SSHClient:
        if self._client is None:
            client = paramiko.SSHClient()
            client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
            self._client = client
        return self._client

    def is_open(self) -> bool:
        if not self._client:
            return False
        transport = self._client.get_transport()
        return bool(transport and transport.is_active())

    def open(self) -> None:
        """Open using provided password or key_path (if set)."""
        if self.is_open():
            return

        if self.key_path:
            self.open_with_key(self.key_path)

        else:
            self.open_with_password(self.password or '')

    def open_with_key(self, key_path: str | os.PathLike, *, disabled_algorithms: dict | None = None) -> None:
        client = self._ensure_client()
        key = paramiko.RSAKey.from_private_key_file(str(key_path))

        try:
            client.connect(
                self.host,
                username=self.username,
                pkey=key,
                timeout=self.timeout,
                disabled_algorithms=disabled_algorithms or {'pubkeys': ['rsa-sha2-256', 'rsa-sha2-512']},
            )

        except Exception as e:
            raise RuntimeError(f"Failed to connect SSH to {self.host} with key: {e}") from e

    def open_with_password(self, password: str, *, disabled_algorithms: dict | None = None) -> None:
        client = self._ensure_client()

        try:
            client.connect(
                self.host,
                username=self.username,
                password=password,
                timeout=self.timeout,
                disabled_algorithms=disabled_algorithms or {'pubkeys': ['rsa-sha2-256', 'rsa-sha2-512']},
            )

        except Exception as e:
            raise RuntimeError(f"Failed to connect SSH to {self.host} with password: {e}") from e

    def close(self) -> None:
        if self._client is not None:
            try:
                self._client.close()

            finally:
                self._client = None

    # --- command execution -----------------------------------------------------
    def exec(self, command: str, *, display_stdout: bool = False, display_stderr: bool = True) -> tuple[bool, list[str]]:
        """Execute a command. Returns (success, lines). Lines are stdout if success, else stderr."""
        if not self.is_open():
            raise RuntimeError("SSHComms.exec() called before connection is open")

        try:
            _, ssh_stdout, ssh_stderr = self._client.exec_command(command)  # type: ignore[union-attr]
            stdout_text = ssh_stdout.read().decode('utf-8', errors='replace')
            stderr_text = ssh_stderr.read().decode('utf-8', errors='replace')
            stdout = [line.strip() for line in stdout_text.split('\n') if line.strip()]
            stderr = [line.strip() for line in stderr_text.split('\n') if line.strip()]

            if stdout and display_stdout:
                for line in stdout:
                    logging.debug(line)

            if stderr:
                if display_stderr:
                    for line in stderr:
                        logging.debug(f"ssh command error: {line}")
                return False, stderr

            return True, stdout

        except (paramiko.SSHException, paramiko.AuthenticationException, paramiko.BadHostKeyException) as e:
            msg = f"ssh connection error: {e}"
            logging.debug(msg)
            return False, [msg]

        except (socket.timeout, socket.error) as e:
            msg = f"ssh socket error: {e}"
            logging.debug(msg)
            return False, [msg]

    # --- SFTP helpers ----------------------------------------------------------
    def open_sftp(self) -> paramiko.SFTPClient:
        if not self.is_open():
            raise RuntimeError("SSHComms.open_sftp() called before connection is open")

        return self._client.open_sftp()  # type: ignore[union-attr]

    def read_file(self, remote_path: str) -> list[str]:
        with self.open_sftp() as sftp:
            with sftp.file(remote_path, 'r') as f:  # type: ignore[attr-defined]
                data = f.read().decode('utf-8', errors='replace')
                return [line for line in (l.strip() for l in data.split('\n')) if line]

    def write_file(self, remote_path: str, content: list[str] | str) -> None:
        text = ''.join(content) if isinstance(content, list) else content
        with self.open_sftp() as sftp:
            with sftp.file(remote_path, 'w') as f:  # type: ignore[attr-defined]
                f.write(text)
