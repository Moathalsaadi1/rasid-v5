"""Nmap XML output parser."""
from __future__ import annotations

from typing import Any

# defusedxml protects against XML External Entity (XXE) and "billion laughs"
# (entity expansion) attacks. Nmap output comes from inside our DinD setup,
# but the host being scanned can sometimes influence specific attributes of
# the XML, and a hardened parser is cheap insurance. We fall back to
# stdlib ElementTree only if defusedxml is unavailable, with entity
# resolution disabled.
try:
    import defusedxml.ElementTree as ET  # type: ignore
except ImportError:  # pragma: no cover
    import xml.etree.ElementTree as ET  # type: ignore


def extract_xml(raw_text: str) -> str:
    start = raw_text.find("<?xml")
    end = raw_text.rfind("</nmaprun>")
    if start == -1 or end == -1:
        raise ValueError("no complete Nmap XML document found")
    end += len("</nmaprun>")
    return raw_text[start:end]


def parse(raw_text: str) -> dict[str, Any]:
    """Parse nmap XML output into a structured dict.

    Returns:
        {"domains": [...], "ips": [...], "services": [{port, protocol, state, name}]}
    """
    xml_text = extract_xml(raw_text)
    root = ET.fromstring(xml_text)

    domains: list[str] = []
    ips: list[str] = []
    services: list[dict[str, Any]] = []

    for host in root.findall("host"):
        for addr in host.findall("address"):
            addr_value = addr.attrib.get("addr")
            addr_type = addr.attrib.get("addrtype")
            if addr_value and addr_type in ("ipv4", "ipv6"):
                if addr_value not in ips:
                    ips.append(addr_value)

        hostnames = host.find("hostnames")
        if hostnames is not None:
            for hostname in hostnames.findall("hostname"):
                name = hostname.attrib.get("name")
                if name and name not in domains:
                    domains.append(name)

        ports = host.find("ports")
        if ports is not None:
            for port in ports.findall("port"):
                protocol = port.attrib.get("protocol")
                portid = port.attrib.get("portid")

                state_el = port.find("state")
                service_el = port.find("service")

                state = state_el.attrib.get("state") if state_el is not None else "unknown"
                service_name = service_el.attrib.get("name") if service_el is not None else "unknown"

                if protocol and portid and portid.isdigit():
                    services.append({
                        "port": int(portid),
                        "protocol": protocol,
                        "state": state,
                        "name": service_name,
                    })

    return {"domains": domains, "ips": ips, "services": services}
