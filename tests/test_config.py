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
from nfv_test_api import config


def test_load_config(tmp_path):
    cfg = """
namespaces:
    - name: LOC1
      interfaces:
        - name: eth0
          mac: "fa:16:3e:31:c8:d8"
    - name: LOC2
      interfaces:
        - name: eth0
          mac: "fa:16:3e:2c:7d:c1"
    - name: LOC3
      interfaces:
        - name: eth0
          mac: "fa:16:3e:81:7d:13"
    - name: LOC4
      interfaces:
        - name: eth0
          mac: "fa:16:3e:33:c6:e3"
    - name: LOC5
      interfaces:
        - name: eth0
          mac: "fa:16:3e:ff:92:8a"
    - name: LOC6
      interfaces:
        - name: eth0
          mac: "fa:16:3e:15:08:dc"
    - name: LOC7
      interfaces:
        - name: eth0
          mac: "fa:16:3e:71:04:b4"
    - name: LOC8
      interfaces:
        - name: eth0
          mac: "fa:16:3e:ed:14:0e"
connection_config:
    timeout_dns_lookup_in_ms: 1000
duration_bandwidth_test_in_sec: 5
hostname_for_dns_lookup: "inmanta.com"
iperf3_server: "10.0.0.36"
"""
    p = tmp_path / "config.yaml"
    p.write_text(cfg)

    cfg = config.get_config(str(p))
    assert len(cfg.namespaces) == 8
