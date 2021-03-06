## old / broken
def set_interface_state(loc, new_status):
    new_status = new_status.lower()
    if new_status not in ["up", "down"]:
        raise exceptions.ServerError(f"Invalid new_state: {new_status}")

    # Set administrative state
    interface = get_config()["locations"][loc]
    args = [
        "ip",
        "netns",
        "exec",
        loc,
        "ip",
        "link",
        "set",
        "dev",
        interface,
        new_status,
    ]
    try:
        subprocess.check_output(args=args).decode()
    except subprocess.CalledProcessError:
        raise exceptions.ServerError(f"Failed to set state of interface {interface} to {new_status} (location={loc})")

    if new_status == "up":
        start_dhclient(loc, interface)
    else:
        remove_ips_from_interface(loc, interface)


def remove_ips_from_interface(loc, interface_name):
    pid_file = get_pid_file(interface_name)
    lease_file = get_lease_file(interface_name)
    bash_command = [
        "bash",
        "-c",
        f"pkill -F {pid_file}; rm -f {pid_file} {lease_file}; ip addr flush dev {interface_name}",
    ]
    args = ["ip", "netns", "exec", loc] + bash_command
    try:
        subprocess.check_output(args=args).decode()
    except subprocess.CalledProcessError:
        raise exceptions.ServerError(f"Failed to remove ips from {interface_name} (location={loc})")


def start_dhclient(loc, interface_name):
    # Start dhclient
    pid_file = get_pid_file(interface_name)
    lease_file = get_lease_file(interface_name)
    args = [
        "ip",
        "netns",
        "exec",
        loc,
        "/sbin/dhclient",
        "-1",
        "-q",
        "-lf",
        lease_file,
        "-pf",
        pid_file,
        interface_name,
    ]
    try:
        subprocess.check_output(args=args, timeout=5).decode()
    except subprocess.CalledProcessError:
        raise exceptions.ServerError(f"Failed to start dhclient (location={loc})")


@app.route("/dns-lookup/<loc>/<dns_server>", methods=["GET"])
def dns_lookup(loc, dns_server):
    hostname_dns_lookup = get_config()["hostname_for_dns_lookup"]
    timeout_in_sec = get_config()["connection_config"]["timeout_dns_lookup_in_ms"] / 1000
    args = [
        "ip",
        "netns",
        "exec",
        loc,
        "dig",
        f"@{dns_server}",
        "+noall",
        "+answer",
        "+stats",
        hostname_dns_lookup,
        "A",
    ]
    try:
        output = subprocess.check_output(timeout=timeout_in_sec, args=args).decode()
    except subprocess.TimeoutExpired:
        raise exceptions.ServerError(
            f"Timeout occured while executing DNS lookup for {hostname_dns_lookup} on DNS server {dns_server} "
            f"(location={loc})"
        )
    except subprocess.CalledProcessError:
        raise exceptions.ServerError(
            f"Failed to execute DNS lookup for {hostname_dns_lookup} on DNS server {dns_server} (location={loc})"
        )
    a_records = []
    query_time = None
    for line in output.split("\n"):
        line = line.strip()
        # Empty line
        if not line:
            continue
        # Line with A record
        if not line.startswith(";;"):
            a_records.append(line)
        # Line with query time
        match = re.search(";; Query time: (?P<query_time>.*) msec", line)
        if match:
            query_time = match.group("query_time").strip()
    return {
        "dns_server": dns_server,
        "a_records": a_records,
        "query_time_msec": int(query_time),
    }


@app.route("/bandwidth/<loc>", methods=["GET"])
def bandwidth(loc):
    iperf3_server = get_config()["iperf3_server"]
    duration_bandwidth_test_in_sec = get_config()["duration_bandwidth_test_in_sec"]
    args = [
        "ip",
        "netns",
        "exec",
        loc,
        "iperf3",
        "-c",
        iperf3_server,
        "-t",
        str(duration_bandwidth_test_in_sec),
        "-J",
    ]
    try:
        output = subprocess.check_output(timeout=duration_bandwidth_test_in_sec + 2, args=args).decode()
    except subprocess.TimeoutExpired:
        raise exceptions.ServerError(f"Timeout occured while executing bandwidth test towards {iperf3_server} (location={loc})")
    except subprocess.CalledProcessError:
        raise exceptions.ServerError(f"Failed to execute bandwidth test towards {iperf3_server} (location={loc})")
    dct = json.loads(output)
    try:
        return {"bandwidth_bits_per_sec": float(dct["end"]["sum_received"]["bits_per_second"])}
    except KeyError:
        raise exceptions.ServerError(f"Failed to extract bandwidth from: {dct}")
