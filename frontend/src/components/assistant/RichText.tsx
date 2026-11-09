import type { ReactNode } from "react";

const H = "[-\u2010-\u2015\u2212]";   // plain or typographic hyphen
const REF = new RegExp(`(?:SOP|RB|REF)${H}[A-Z]+${H}\\d{3}\\s*§\\s*\\d+(?:\\.\\d+)*`, "g");
const HEADING = /^\s*#{1,6}\s+(.+?)\s*#*\s*$/;
const TABLE_ROW = /^\s*\|.*\|\s*$/;
const TABLE_SEP = /^\s*\|?\s*:?-{3,}:?\s*(\|\s*:?-{3,}:?\s*)*\|?\s*$/;
const RULE = /^\s*(-{3,}|\*{3,}|_{3,})\s*$/;
const INLINE = /\*\*([^*]+)\*\*|\[([^[\]]+)\]/g;
const OL_ITEM = /^\s*\d+[.)]\s+/;
const UL_ITEM = /^\s*[-*•]\s+/;

interface Props {
  text: string;
  validRefs?: Set<string>;          // refs the backend verified; others are flagged
  onCite?: (ref: string) => void;   // click on a citation chip
}

type Block = { kind: "p" | "ol" | "ul" | "h" | "table"; items: string[] };

const normRef = (r: string) => r.replace(/[\u2010-\u2015\u2212]/g, "-").replace(/\s*§\s*/, " §");
const cells = (row: string) => row.trim().replace(/^\||\|$/g, "").split("|").map((c) => c.trim());

/** Line-based parse: list items start with "1." or "-"; indented lines after an item continue it;
 *  an unindented line after a list starts a new paragraph; blank lines end a block. */
function parse(text: string): Block[] {
  const blocks: Block[] = [];
  let cur: Block | null = null;
  for (const raw of text.replace(/\r/g, "").split("\n")) {
    const line = raw.trim();
    if (!line || RULE.test(raw)) { cur = null; continue; }
    const h = HEADING.exec(raw);
    if (h) { blocks.push({ kind: "h", items: [h[1]] }); cur = null; continue; }
    if (TABLE_ROW.test(raw)) {
      if (TABLE_SEP.test(raw)) continue;
      if (!cur || cur.kind !== "table") { cur = { kind: "table", items: [] }; blocks.push(cur); }
      cur.items.push(line);
      continue;
    }
    if (cur?.kind === "table") cur = null;
    const kind = OL_ITEM.test(raw) ? "ol" : UL_ITEM.test(raw) ? "ul" : null;
    if (kind) {
      if (!cur || cur.kind !== kind) { cur = { kind, items: [] }; blocks.push(cur); }
      cur.items.push(raw.replace(kind === "ol" ? OL_ITEM : UL_ITEM, "").trim());
    } else if (cur && (cur.kind === "p" || /^\s/.test(raw))) {
      cur.items[cur.items.length - 1] += " " + line;   // wrapped paragraph, or indented list continuation
    } else {
      cur = { kind: "p", items: [line] }; blocks.push(cur);
    }
  }
  return blocks;
}

/** Minimal, safe Markdown: paragraphs, headings, numbered and bulleted lists, tables, **bold**, and
 *  [DOC §n] citations.
 *  Builds React elements only; never injects HTML from the model. */
export function RichText({ text, validRefs, onCite }: Props) {
  function inline(line: string, key: string): ReactNode[] {
    const out: ReactNode[] = [];
    let last = 0, n = 0;
    for (const m of line.matchAll(INLINE)) {
      if (m.index! > last) out.push(line.slice(last, m.index));
      if (m[1]) out.push(<strong key={`${key}b${n++}`}>{m[1]}</strong>);
      else {
        const refs = m[2].match(REF);
        if (!refs) out.push(m[0]);
        else refs.map(normRef).forEach((ref) => {
          const valid = !validRefs || validRefs.has(ref);
          out.push(
            <button key={`${key}c${n++}`} type="button" className={valid ? "cite" : "cite cite-invalid"}
                    onClick={() => onCite?.(ref)}
                    title={valid ? `Open ${ref}` : "Not found in the sources the assistant was given"}>
              {ref}{!valid && " ⚠"}
            </button>,
          );
        });
      }
      last = m.index! + m[0].length;
    }
    if (last < line.length) out.push(line.slice(last));
    return out;
  }

  return (
    <div className="richtext">
      {parse(text).map((b, bi) => {
        if (b.kind === "p") return <p key={bi}>{inline(b.items[0], `${bi}`)}</p>;
        if (b.kind === "h") return <p key={bi} className="rt-heading"><strong>{inline(b.items[0], `${bi}`)}</strong></p>;
        if (b.kind === "table") {
          const [head, ...rows] = b.items.map(cells);
          return (
            <div key={bi} className="table-wrap">
              <table className="rt-table">
                <thead><tr>{head.map((c, ci) => <th key={ci}>{inline(c, `${bi}-h${ci}`)}</th>)}</tr></thead>
                <tbody>{rows.map((r, ri) => (
                  <tr key={ri}>{r.map((c, ci) => <td key={ci}>{inline(c, `${bi}-${ri}-${ci}`)}</td>)}</tr>
                ))}</tbody>
              </table>
            </div>
          );
        }
        const items = b.items.map((it, i) => <li key={i}>{inline(it, `${bi}-${i}`)}</li>);
        return b.kind === "ol" ? <ol key={bi}>{items}</ol> : <ul key={bi}>{items}</ul>;
      })}
    </div>
  );
}
