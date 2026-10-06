#!/usr/bin/env python3
"""Audit observable Codex skill reads without exporting conversation content.

Standard-library only. Public aggregates contain skill names and counts. The
private audit contains local file references and hashes, never command/output
text. An observable read is not proof that a skill was followed or effective.
"""
from __future__ import annotations
import argparse
import collections
import csv
import datetime as dt
import hashlib
import json
import pathlib
import re
import time

UTC = dt.timezone.utc
TS = re.compile(r'^\s*\{"timestamp"\s*:\s*"([^"]+)"')
CALL_TYPES = {"function_call", "custom_tool_call"}
OUTPUT_TYPES = {"function_call_output", "custom_tool_call_output"}


def digest(value):
    if not isinstance(value, str):
        value = json.dumps(value, ensure_ascii=False, sort_keys=True)
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def parse_time(value):
    return dt.datetime.fromisoformat(value.replace("Z", "+00:00")).astimezone(UTC)


def flatten_output(value):
    if isinstance(value, str):
        return value
    if isinstance(value, list):
        return "\n".join(flatten_output(x) for x in value)
    if isinstance(value, dict):
        if "text" in value:
            return flatten_output(value["text"])
        if "output" in value:
            return flatten_output(value["output"])
        return json.dumps(value, ensure_ascii=False)
    return str(value or "")


def decode_js_literal(raw, quote):
    if quote == '"':
        try:
            return json.loads(quote + raw + quote)
        except ValueError:
            pass
    replacements = {"n": "\n", "r": "\r", "t": "\t", "\\": "\\",
                    "'": "'", '"': '"', "`": "`", "$": "$"}
    return re.sub(r"\\(.)", lambda m: replacements.get(m[1], "\\" + m[1]), raw)


def js_literals(code):
    """Return string spans; comments are skipped. No execution of input code."""
    found = []
    i = 0
    while i < len(code):
        if code.startswith("//", i):
            j = code.find("\n", i + 2)
            i = len(code) if j < 0 else j + 1
            continue
        if code.startswith("/*", i):
            j = code.find("*/", i + 2)
            i = len(code) if j < 0 else j + 2
            continue
        if code[i] not in "\"'`":
            i += 1
            continue
        start, quote = i, code[i]
        i += 1
        body_start = i
        while i < len(code):
            if code[i] == "\\":
                i += 2
            elif code[i] == quote:
                found.append((start, i + 1, decode_js_literal(code[body_start:i], quote)))
                i += 1
                break
            else:
                i += 1
    return found


def command_texts(name, arguments):
    """Extract direct shell commands and static cmd literals nested in exec."""
    if isinstance(arguments, str):
        try:
            obj = json.loads(arguments)
        except ValueError:
            obj = None
    else:
        obj = arguments
    if isinstance(obj, dict):
        if isinstance(obj.get("cmd"), str):
            return [obj["cmd"]]
        if isinstance(obj.get("command"), str):
            return [obj["command"]]
        if isinstance(obj.get("path"), str) and re.search(r"read|file", name, re.I):
            return ["read_file " + repr(obj["path"])]
        return []
    if not isinstance(arguments, str):
        return []
    # Custom tools carry JavaScript directly. Resolve simple static bindings.
    literals = js_literals(arguments)
    bindings = {}
    for start, end, value in literals:
        prefix = arguments[max(0, start - 100):start]
        m = re.search(r"(?:const|let|var)\s+(\w+)\s*=\s*$", prefix)
        if m:
            bindings[m[1]] = value
    commands = []
    for start, end, value in literals:
        prefix = arguments[max(0, start - 35):start]
        if re.search(r"\b(?:cmd|command)\s*:\s*$", prefix):
            value = re.sub(r"\$\{(\w+)\}", lambda m: bindings.get(m[1], m[0]), value)
            commands.append(value)
    for m in re.finditer(r"\b(?:cmd|command)\s*:\s*(\w+)\s*[,}]", arguments):
        if m[1] in bindings:
            commands.append(bindings[m[1]])
    # ReadAllText / read_text calls outside cmd also qualify when literal.
    if not commands and re.search(r"ReadAllText|\.read_text\(|\bread_file\b", arguments):
        commands.append(arguments)
    return commands


def skill_candidates(name, arguments):
    candidates = {}
    commands = command_texts(name, arguments)
    for command in commands:
        # Segmenting shell statements avoids counting rg/list operations that
        # happen to share a tool call with unrelated Get-Content operations.
        for segment in re.split(r"[;\n]|\s+&&\s+", command):
            if not re.search(r"(?:\bGet-Content\b|(?:^|\s)(?:cat|type)\s+|ReadAllText\s*\(|\.read_text\s*\(|\bread_file\s+)", segment, re.I):
                continue
            # Quotes support Windows paths with spaces. Bare paths are also
            # supported. Variable/dynamic paths are deliberately unresolved.
            paths = re.findall(r"['\"]([^'\"]*?[\\/]SKILL\.md)['\"]", segment, re.I)
            paths += re.findall(r"(?<![\w'\"])([^\s'\";,()]+[\\/]SKILL\.md)(?![\w])", segment, re.I)
            for path in paths:
                path = path.replace("\\\\", "\\").replace("/", "\\")
                bits = path.rstrip("\\").split("\\")
                if len(bits) < 2 or "$" in path or "{" in path:
                    continue
                skill = bits[-2]
                if not re.fullmatch(r"[A-Za-z0-9_.-]+", skill):
                    continue
                candidates[skill] = {"skill": skill, "path_hash": digest(path.lower()),
                                     "reader": "read_text" if "read_text" in segment else
                                     "ReadAllText" if "ReadAllText" in segment else
                                     "Get-Content" if re.search("Get-Content", segment, re.I) else "cat/type/read_file"}
    return list(candidates.values())


def evidence_status(output, skill):
    text = flatten_output(output)
    # Nested exec results often serialize shell output as a JSON string.
    text = (text.replace("\\r\\n", "\n").replace("\\n", "\n")
            .replace("\\r", "").replace("\\t", "\t")
            .replace('\\"', '"').replace("\\'", "'"))
    names = re.findall(r"(?:^|\n)\s*name:\s*[\"']?([^\n\"']+)", text, re.I)
    normalize = lambda s: re.sub(r"[^a-z0-9]", "", s.lower())
    expected = normalize(skill)
    matched = any(normalize(n.strip()).endswith(expected) or
                  expected.endswith(normalize(n.strip())) for n in names if normalize(n.strip()))
    header = bool(re.search(r"(?:^|\n)\s*description:\s*\S", text, re.I))
    if matched and header and len(text) > 200:
        return "confirmed", "skill_frontmatter_returned"
    failures = bool(re.search(r"Cannot find path|does not exist|No such file|FileNotFoundError|Get-Content\s*:|Permission denied|Access.*denied", text, re.I))
    if failures:
        return "unconfirmed", "read_error_or_no_matching_body"
    return "unconfirmed", "missing_matching_skill_frontmatter"


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--sessions", type=pathlib.Path, required=True)
    ap.add_argument("--output", type=pathlib.Path, required=True)
    ap.add_argument("--start", required=True, help="ISO timestamp, with timezone")
    ap.add_argument("--end", required=True, help="Exclusive ISO timestamp, with timezone")
    ap.add_argument("--utc-offset-hours", type=int, default=8)
    ap.add_argument("--target", default="proactive-problem-solving")
    ap.add_argument("--scan-all", action="store_true", help="Disable modification-time prefilter")
    args = ap.parse_args()
    start, end = parse_time(args.start), parse_time(args.end)
    start_s, end_s = start.isoformat().replace("+00:00", "Z"), end.isoformat().replace("+00:00", "Z")
    local = dt.timezone(dt.timedelta(hours=args.utc_offset_hours))
    args.output.mkdir(parents=True, exist_ok=True)
    all_files = sorted(args.sessions.rglob("*.jsonl"))
    files = [f for f in all_files if args.scan_all or f.stat().st_mtime >= start.timestamp()]
    diagnostics = collections.Counter()
    events = {}
    metadata = {}
    candidate_events = {}
    unresolved = {}
    outputs = {}
    began = time.monotonic()
    print(json.dumps({"phase": "scan", "files": len(files), "bytes": sum(f.stat().st_size for f in files)}), flush=True)
    for file_index, file in enumerate(files):
        sid = None
        created = ""
        parent = None
        with file.open("r", encoding="utf-8", errors="strict") as handle:
            for line_no, line in enumerate(handle, 1):
                if '"session_meta"' in line[:160]:
                    try:
                        record = json.loads(line)
                    except (ValueError, UnicodeError):
                        diagnostics["malformed_records"] += 1
                        continue
                    p = record.get("payload", {})
                    sid = p.get("id") or p.get("session_id")
                    created = p.get("timestamp") or record.get("timestamp", "")
                    parent = p.get("parent_thread_id")
                    metadata[sid] = {"created": created, "parent": parent, "file": str(file)}
                    continue
                match = TS.match(line)
                if not match:
                    continue
                ts = match[1]
                # All observed event timestamps use UTC ISO. A cheap prefix
                # comparison removes giant out-of-window context records.
                if not start_s[:19] <= ts[:19] < end_s[:19]:
                    continue
                if '"response_item"' not in line[:160] or "tool_call" not in line and "function_call" not in line:
                    continue
                try:
                    record = json.loads(line)
                except (ValueError, UnicodeError):
                    diagnostics["malformed_records"] += 1
                    continue
                p = record.get("payload", {})
                typ = p.get("type")
                if typ not in CALL_TYPES | OUTPUT_TYPES:
                    continue
                if sid is None:
                    diagnostics["records_without_session_id"] += 1
                    continue
                when = parse_time(ts)
                if not start <= when < end:
                    continue
                call_id = p.get("call_id") or p.get("id")
                if typ in CALL_TYPES:
                    name = p.get("name", "")
                    arguments = p.get("arguments", p.get("input", ""))
                    key = digest([call_id, name, arguments, ts])
                    occ = {"session_id": sid, "source_file": str(file), "call_line": line_no,
                           "created": created, "parent": parent}
                    if key not in events:
                        events[key] = {"timestamp": ts, "call_id_hash": digest(call_id), "occurrences": [], "name": name}
                    events[key]["occurrences"].append(occ)
                    if "SKILL.md" in str(arguments):
                        diagnostics["literal_skill_token_tool_call_occurrences"] += 1
                        candidates = skill_candidates(name, arguments)
                        if candidates:
                            candidate_events[key] = {"candidates": candidates, "argument_hash": digest(arguments)}
                        else:
                            diagnostics["skill_token_not_resolved_to_literal_reader"] += 1
                            unresolved[key] = {"event_hash": key, "session_hash": digest(sid),
                                               "source_file": str(file), "call_line": line_no,
                                               "tool_name": name, "argument_hash": digest(arguments)}
                    # Pair output using session + call id; outputs must remain
                    # isolated across forks even when call ids are copied.
                    outputs.setdefault((sid, call_id), {"event_key": key})
                else:
                    pair = outputs.setdefault((sid, call_id), {})
                    pair["output_hash"] = digest(p.get("output"))
                    pair["output_line"] = line_no
                    pair["output_source_file"] = str(file)
                    # Keep only candidate output text temporarily, not on disk.
                    key = pair.get("event_key")
                    if key in candidate_events:
                        pair["statuses"] = {c["skill"]: evidence_status(p.get("output"), c["skill"])
                                            for c in candidate_events[key]["candidates"]}
        if (file_index + 1) % 10 == 0:
            print(json.dumps({"phase": "scan", "processed_files": file_index + 1, "tool_events": len(events), "seconds": round(time.monotonic() - began, 1)}), flush=True)

    # A copied event is attributed to its earliest eligible originating session
    # (created no later than the call). Fallback is deterministic and audited.
    audit = []
    session_tools = set()
    daily_tools = collections.defaultdict(set)
    confirmed = []
    duplicate_occurrences = 0
    for key, event in events.items():
        occurrences = event["occurrences"]
        duplicate_occurrences += len(occurrences) - 1
        eligible = [o for o in occurrences if o["created"] and o["created"][:19] <= event["timestamp"][:19]]
        if not eligible:
            eligible = occurrences
            diagnostics["canonical_origin_fallback"] += 1
        origin = min(eligible, key=lambda o: (o["created"], o["session_id"], o["call_line"]))
        sid = origin["session_id"]
        day = parse_time(event["timestamp"]).astimezone(local).date().isoformat()
        session_tools.add(sid)
        daily_tools[day].add(sid)
        if key not in candidate_events:
            continue
        candidate = candidate_events[key]
        matching_pairs = [p for p in outputs.values() if p.get("event_key") == key and "statuses" in p]
        for c in candidate["candidates"]:
            successful_pairs = [p for p in matching_pairs if p["statuses"].get(c["skill"], (None,))[0] == "confirmed"]
            best = successful_pairs[0] if successful_pairs else matching_pairs[0] if matching_pairs else {}
            status, reason = best.get("statuses", {}).get(c["skill"], ("unconfirmed", "missing_output"))
            item = {"event_hash": key, "session_hash": digest(sid), "timestamp_utc": event["timestamp"],
                    "local_day": day, "skill": c["skill"], "status": status, "reason": reason,
                    "reader": c["reader"], "argument_hash": candidate["argument_hash"],
                    "output_hash": best.get("output_hash"), "source_file": origin["source_file"],
                    "call_line": origin["call_line"], "output_line": best.get("output_line"),
                    "output_source_file": best.get("output_source_file"),
                    "replicated_occurrences": len(occurrences) - 1, "path_hash": c["path_hash"]}
            audit.append(item)
            if status == "confirmed":
                confirmed.append(item)
    skills = collections.defaultdict(lambda: {"sessions": set(), "reads": 0})
    any_skill_sessions = set()
    daily_skills = collections.defaultdict(set)
    daily_reads = collections.Counter()
    daily_target = collections.defaultdict(set)
    for row in confirmed:
        skills[row["skill"]]["sessions"].add(row["session_hash"])
        skills[row["skill"]]["reads"] += 1
        any_skill_sessions.add(row["session_hash"])
        daily_skills[row["local_day"]].add(row["session_hash"])
        daily_reads[row["local_day"]] += 1
        if row["skill"] == args.target:
            daily_target[row["local_day"]].add(row["session_hash"])
    ranking = [{"skill": s, "sessions": len(v["sessions"]), "confirmed_reads": v["reads"]}
               for s, v in skills.items()]
    ranking.sort(key=lambda r: (-r["sessions"], -r["confirmed_reads"], r["skill"]))
    for row in ranking:
        row["rank"] = 1 + sum(x["sessions"] > row["sessions"] for x in ranking)
        row["share_of_tool_sessions_pct"] = round(100 * row["sessions"] / len(session_tools), 2) if session_tools else 0
        row["share_of_skill_reading_sessions_pct"] = round(100 * row["sessions"] / len(any_skill_sessions), 2) if any_skill_sessions else 0
    days = []
    day = start.astimezone(local).date()
    while day < end.astimezone(local).date():
        ds = day.isoformat()
        days.append({"date": ds, "tool_active_sessions": len(daily_tools[ds]),
                     "skill_reading_sessions": len(daily_skills[ds]), "confirmed_skill_reads": daily_reads[ds],
                     "target_skill_sessions": len(daily_target[ds])})
        day += dt.timedelta(days=1)
    target = next((r for r in ranking if r["skill"] == args.target), None)
    safe = {"schema_version": 1, "measurement": "observable_confirmed_skill_file_reads",
            "window": {"start": args.start, "end_exclusive": args.end, "utc_offset_hours": args.utc_offset_hours},
            "coverage": {"files_in_inventory": len(all_files), "files_scanned": len(files),
                         "tool_active_sessions": len(session_tools), "skill_reading_sessions": len(any_skill_sessions),
                         "distinct_skills_confirmed": len(ranking), "confirmed_skill_reads": len(confirmed),
                         "unique_tool_call_events": len(events), "copied_call_occurrences_removed": duplicate_occurrences,
                         "unconfirmed_skill_read_candidates": sum(r["status"] != "confirmed" for r in audit)},
            "target": target, "ranking": ranking, "daily": days,
            "caveat": "Personal local observable file reads, not global automatic invocation rate or evidence of effectiveness."}
    (args.output / "safe_aggregate.json").write_text(json.dumps(safe, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    for filename, rows in (("skills.csv", ranking), ("daily.csv", days)):
        with (args.output / filename).open("w", encoding="utf-8-sig", newline="") as handle:
            if rows:
                writer = csv.DictWriter(handle, fieldnames=list(rows[0]))
                writer.writeheader()
                writer.writerows(rows)
    with (args.output / "private_evidence.jsonl").open("w", encoding="utf-8") as handle:
        for row in audit:
            handle.write(json.dumps(row, ensure_ascii=False) + "\n")
    with (args.output / "private_unresolved.jsonl").open("w", encoding="utf-8") as handle:
        for row in unresolved.values():
            handle.write(json.dumps(row, ensure_ascii=False) + "\n")
    private = {"diagnostics": diagnostics, "source_inventory_sha256": digest([str(f) for f in files]),
               "session_metadata_records": len(metadata), "duration_seconds": round(time.monotonic() - began, 2),
               "candidate_statuses": dict(collections.Counter(r["reason"] for r in audit)),
               "tool_names": dict(collections.Counter(e["name"] for e in events.values()))}
    (args.output / "private_audit_summary.json").write_text(json.dumps(private, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"phase": "complete", "coverage": safe["coverage"], "target": target,
                      "diagnostics": dict(diagnostics), "seconds": private["duration_seconds"]}, ensure_ascii=False), flush=True)


if __name__ == "__main__":
    main()
