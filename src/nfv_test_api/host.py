import logging
import subprocess
from typing import List, Tuple

LOGGER = logging.getLogger(__name__)


class Host:
    def __init__(self, shell_entry_point: List[str] = []) -> None:
        self._shell_entry_point = shell_entry_point

    def exec(self, command: List[str]) -> Tuple[str, str]:
        cmd = self._shell_entry_point + command
        LOGGER.debug("Running command %s", cmd)
        process = subprocess.Popen(cmd, shell=False, universal_newlines=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE,)
        return process.communicate()

    def hostname(self) -> str:
        stdout, stderr = self.exec(["hostname"])
        if stderr:
            raise RuntimeError(f"Failed to run hostname command on host: {stderr}")

        return stdout.strip()


class NamespaceHost(Host):
    def __init__(self, namespace: str) -> None:
        super().__init__(shell_entry_point=["ip", "netns", "exec", namespace])

    def get_raw_namespaces(self) -> List[object]:
        raise NotImplementedError("You shouldn't try to interact with namespaces from inside another one")
