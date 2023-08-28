"""
       Copyright 2021 Inmanta

   Licensed under the Apache License, Version 2.0 (the "License");
   you may not use this file except in compliance with the License.
   You may obtain a copy of the License at

       http://www.apache.org/licenses/LICENSE-2.0

   Unless required by applicable law or agreed to in writing, software
   distributed under the License is distributed on an "AS IS" BASIS,
   WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
   See the License for the specific language governing permissions and
   limitations under the License.
"""
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
        process = subprocess.Popen(
            cmd,
            shell=False,
            universal_newlines=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )
        try:
            # Make sure our command terminates.
            # We set a hard timeout of 10 seconds, it should work for all
            # the commands we run.  If it doesn't, we can create a more
            # elaborate mechanism.
            return process.communicate(timeout=10)
        except subprocess.TimeoutExpired:
            # Kill the process and return the output we had so far
            process.terminate()
            return process.communicate(timeout=1)

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
