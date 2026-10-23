#!/usr/bin/env python3
"""Offline verification for the revision-pinned, licence-reviewed LegalBench snapshot."""
import argparse, csv, hashlib, io, json, sys, tarfile
from pathlib import Path, PurePosixPath

ROOT=Path(__file__).resolve().parents[2]
ARCHIVE_SHA="f2eed6bdf3bf08d5837c33c04634e1fbb32544ac1d0e1eeacd20e034ce0ade0a"
REVISION="daec8237410aa23e3faf4bc41ad8b3a7e1696826"
DEFAULT_ARCHIVE=ROOT/"data/public/legalbench/extra-licensed-snapshots-v1.tar.gz"
DEFAULT_MANIFEST=ROOT/"data/manifests/legalbench.json"

class VerificationError(ValueError): pass

def digest(data): return hashlib.sha256(data).hexdigest()

def safe_path(name):
    path=PurePosixPath(name)
    if path.is_absolute() or not path.parts or any(p in ("", ".", "..") for p in path.parts) or "\\" in name:
        raise VerificationError(f"Unsafe archive path: {name!r}")
    return path

def verify_split(task, split, raw, normalized, sidecar_bytes, info, revision=REVISION):
    try: side=json.loads(sidecar_bytes.decode("utf-8"))
    except (UnicodeDecodeError,json.JSONDecodeError) as e: raise VerificationError(f"{task}/{split}: invalid sidecar: {e}") from e
    if info.get("status")!="approved" or info.get("redistribution_allowed_with_attribution") is not True or info.get("license_spdx")!="CC-BY-4.0":
        raise VerificationError(f"{task}/{split}: task licence is not approved")
    expected={"task":task,"split":split,"upstream_revision":revision,"task_license_spdx":"CC-BY-4.0",
              "task_license":info.get("task_license"),"task_license_url":info.get("license_url"),
              "official_task_page":info.get("task_page"),"attribution":info.get("attribution"),
              "allowed_labels":info.get("labels"),"raw_sha256":digest(raw),"raw_bytes":len(raw),
              "normalized_jsonl_sha256":digest(normalized),"normalized_jsonl_bytes":len(normalized)}
    for k,v in expected.items():
        if side.get(k)!=v: raise VerificationError(f"{task}/{split}: sidecar mismatch for {k}")
    if revision not in side.get("upstream_source_url",""): raise VerificationError(f"{task}/{split}: source URL is not revision-pinned")
    try: reader=csv.DictReader(io.StringIO(raw.decode("utf-8-sig"),newline=""),delimiter="\t")
    except UnicodeDecodeError as e: raise VerificationError(f"{task}/{split}: TSV encoding error") from e
    if not reader.fieldnames or not {"index","answer"}.issubset(reader.fieldnames): raise VerificationError(f"{task}/{split}: missing index/answer columns")
    if side.get("columns")!=reader.fieldnames: raise VerificationError(f"{task}/{split}: column metadata mismatch")
    source=[]; indexes=set()
    for line,row in enumerate(reader,2):
        if None in row: raise VerificationError(f"{task}/{split}: malformed row at line {line}")
        try: idx=int(row["index"])
        except (ValueError,TypeError) as e: raise VerificationError(f"{task}/{split}: bad index at line {line}") from e
        if idx in indexes: raise VerificationError(f"{task}/{split}: duplicate index {idx}")
        indexes.add(idx); fields=dict(row); fields["index"]=idx
        source.append({"index":idx,"task":task,"split":split,"fields":fields})
    try: actual=[json.loads(line) for line in normalized.decode("utf-8").splitlines() if line.strip()]
    except (UnicodeDecodeError,json.JSONDecodeError) as e: raise VerificationError(f"{task}/{split}: invalid JSONL") from e
    if source!=actual or len(source)!=side.get("rows_written"): raise VerificationError(f"{task}/{split}: TSV/JSONL/sidecar rows differ")
    labels={str(x).strip().casefold() for x in info.get("labels",[])}
    found={str(r["fields"].get("answer","")).strip().casefold() for r in source}
    if not found.issubset(labels): raise VerificationError(f"{task}/{split}: labels outside approved inventory: {sorted(found-labels)}")
    return {"task":task,"split":split,"rows":len(source),"raw_sha256":digest(raw),"jsonl_sha256":digest(normalized)}

def verify_archive(archive_path, manifest_path, expected_sha=ARCHIVE_SHA, revision=REVISION):
    manifest=json.loads(Path(manifest_path).read_text(encoding="utf-8"))
    tasks=manifest.get("task_allowlist")
    if not isinstance(tasks,dict) or not tasks: raise VerificationError("No task allowlist")
    blob=Path(archive_path).read_bytes(); sha=digest(blob)
    if expected_sha and sha!=expected_sha: raise VerificationError(f"Archive SHA mismatch: {sha}")
    try: tar=tarfile.open(fileobj=io.BytesIO(blob),mode="r:gz")
    except tarfile.TarError as e: raise VerificationError(f"Invalid gzip tar: {e}") from e
    with tar:
        members={}
        for m in tar.getmembers():
            path=safe_path(m.name)
            if not m.isfile(): raise VerificationError(f"Non-file tar member: {m.name}")
            if m.name in members: raise VerificationError(f"Duplicate tar member: {m.name}")
            if len(path.parts)!=5 or path.parts[:3] != ("data","public","legalbench"): raise VerificationError(f"Unexpected path: {m.name}")
            members[m.name]=m
        reports=[]; expected=set()
        for task,info in sorted(tasks.items()):
            for split in ("train","test"):
                prefix=f"data/public/legalbench/{task}/{split}"
                names={"tsv":prefix+".tsv","jsonl":prefix+".jsonl","sidecar":prefix+".run-manifest.json"}
                expected.update(names.values())
                if any(n not in members for n in names.values()): raise VerificationError(f"Missing files for {task}/{split}")
                payload={}
                for k,n in names.items():
                    f=tar.extractfile(members[n])
                    if f is None: raise VerificationError(f"Cannot read {n}")
                    payload[k]=f.read()
                reports.append(verify_split(task,split,payload["tsv"],payload["jsonl"],payload["sidecar"],info,revision))
        extras=set(members)-expected
        if extras: raise VerificationError(f"Unexpected archive files: {sorted(extras)[:10]}")
    return {"archive_sha256":sha,"archive_bytes":len(blob),"task_count":len(tasks),"split_count":len(reports),"file_count":len(members),
            "train_rows":sum(r["rows"] for r in reports if r["split"]=="train"),
            "test_rows":sum(r["rows"] for r in reports if r["split"]=="test"),
            "total_rows":sum(r["rows"] for r in reports),"upstream_revision":revision,"splits":reports}

def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("--archive",type=Path,default=DEFAULT_ARCHIVE)
    p.add_argument("--manifest",type=Path,default=DEFAULT_MANIFEST)
    p.add_argument("--expected-archive-sha256",default=ARCHIVE_SHA)
    p.add_argument("--expected-revision",default=REVISION)
    a=p.parse_args()
    try: result=verify_archive(a.archive,a.manifest,a.expected_archive_sha256,a.expected_revision)
    except (VerificationError,OSError,json.JSONDecodeError) as e:
        print(f"verification failed: {e}",file=sys.stderr); return 2
    print(json.dumps(result,ensure_ascii=False,indent=2)); return 0
if __name__=="__main__": raise SystemExit(main())
