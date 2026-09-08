"""Read-only Telnet inventory parsers for MA2 show pools."""
from __future__ import annotations
import re

class PresetProvider:
    preset_types = ("DIMMER", "POSITION", "GOBO", "COLOR", "BEAM", "FOCUS", "CONTROL", "ALL")
    def command(self, preset_type: str) -> str:
        kind = preset_type.upper()
        if kind not in self.preset_types: raise ValueError("Unsupported Preset type.")
        return f"List Preset {kind.title()}"
    def parse(self, output: str, preset_type: str) -> list[dict]:
        rows=[]
        for line in output.splitlines():
            # Verified grandMA2 3.9 table form, for example:
            # ``Focus 6.2 6.2  normal     Normal``.  The first token and
            # pool reference are authoritative; do not collapse it to an
            # arbitrary ALL-pool number.
            table = re.match(r"^\s*(?P<kind>[A-Za-z]+)\s+(?P<reference>\d+\.\d+)\s+\d+\.\d+\s+(?P<name>.+?)\s+(?:Normal|Selective|Global)\s*$", line, re.I)
            if table:
                kind, reference = table.group("kind").upper(), table.group("reference")
                rows.append({"preset_type": kind, "number": int(reference.split(".", 1)[1]), "reference": reference, "name": table.group("name").strip()})
                continue
            match=re.search(r"(?:preset\s+)?(?:[A-Za-z]+\s+)?(?:\d+\.)?(\d+)\s+['\"]?(.+?)['\"]?\s*$", line.strip(), re.I)
            if match and not line.strip().lower().startswith(("executing", "no.")):
                rows.append({"preset_type":preset_type.upper(),"number":int(match.group(1)),"name":match.group(2).strip().strip("'\"")})
        return rows

class EffectProvider:
    command="List Effect"
    _row=re.compile(r"^\s*(?:effect\s+)?(\d+)\s+['\"]?(.+?)['\"]?(?:\s+(.*))?$",re.I)
    def parse(self, output: str) -> list[dict]:
        rows=[]
        for line in output.splitlines():
            clean=line.strip()
            quoted=re.match(r"^\s*(?:effect\s+)?(\d+)\s+['\"]([^'\"]+)['\"]\s*(.*)$", clean, re.I)
            match=self._row.match(clean)
            if not match or line.strip().lower().startswith(("executing", "no.")): continue
            number=int(quoted.group(1)) if quoted else int(match.group(1))
            name=quoted.group(2).strip() if quoted else match.group(2).strip().strip("'\"")
            meta=quoted.group(3) if quoted else match.group(3) or ""
            # grandMA2's tabular `List Effect` output repeats the pool number in
            # the first data column: `Effect 2500 2500  My Label (1)`.  That
            # duplicate is not the label.  Keep the normal/quoted parser for
            # other MA2 output shapes, but decode this verified table form so
            # read-back can attest to the label created by an approved plan.
            if not quoted and name == str(number) and meta.strip():
                table_label = re.sub(r"\s+\(\d+\)\s*$", "", meta).strip()
                if table_label:
                    name = table_label
                    meta = ""
            attributes=[item.strip() for item in re.split(r"[,/]", re.search(r"attributes?\s*[:=]\s*(.+)",meta,re.I).group(1))] if re.search(r"attributes?\s*[:=]\s*(.+)",meta,re.I) else []
            lines=re.search(r"lines?\s*[:=]?\s*(\d+)",meta,re.I)
            kind=re.search(r"\b(template|selective)\b",meta,re.I)
            rows.append({"number":number,"name":name,"kind":kind.group(1).upper() if kind else None,"line_count":int(lines.group(1)) if lines else None,"attributes":attributes})
        return rows

    @staticmethod
    def diagnostics(rows: list[dict]) -> dict:
        numbers=[item["number"] for item in rows]
        unlabeled=[item for item in rows if not str(item.get("name") or "").strip() or str(item.get("name")).strip()==str(item["number"])]
        return {"parsed_count":len(rows),"min_effect_number":min(numbers) if numbers else None,"max_effect_number":max(numbers) if numbers else None,"labeled_count":len(rows)-len(unlabeled),"unlabeled_count":len(unlabeled)}

class PageProvider:
    command="List Page"
    _row=re.compile(r"^\s*(?:page\s+)?(\d+)\s+['\"]?(.+?)['\"]?\s*$",re.I)
    def parse(self, output: str) -> list[dict]:
        return [{"number":int(m.group(1)),"name":m.group(2).strip().strip("'\"")} for line in output.splitlines() if (m:=self._row.match(line.strip())) and not line.strip().lower().startswith(("executing","no."))]

class ExecutorProvider:
    command="List Executor"
    _row=re.compile(r"^\s*(?:executor|exec)\s+(?:(\d+)\.)?(\d+)\s*(.*)$",re.I)
    def parse(self, output: str) -> list[dict]:
        rows=[]
        for line in output.splitlines():
            match=self._row.match(line.strip())
            if not match: continue
            page, number, rest=match.groups(); sequence=re.search(r"sequence\s+(\d+)",rest,re.I); effect=re.search(r"effect\s+(\d+)",rest,re.I); macro=re.search(r"macro\s+(\d+)",rest,re.I)
            assignment=("sequence",int(sequence.group(1))) if sequence else ("effect",int(effect.group(1))) if effect else ("macro",int(macro.group(1))) if macro else (None,None)
            label=re.search(r"['\"]([^'\"]+)['\"]",rest)
            rows.append({"page":int(page) if page else None,"executor":int(number),"location":f"{page+'.' if page else ''}{number}","assignment_type":assignment[0],"assignment":assignment[1],"label":label.group(1) if label else rest.strip() or None})
        return rows
