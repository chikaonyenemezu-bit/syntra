import type { ReactNode } from "react";

const REF = /(?:SOP|RB|REF)-[A-Z]+-\d{3}\s*§\s*\d+(?:\.\d+)*/g;
const INLINE = /\*\*([^*]+)\*\*|\[([^[\]]+)\]/g;
const OL_ITEM = /^\s*\d+[.)]\s+/;
const UL_ITEM = /^\s*[-*•]\s+/;

interface Props {
  text: string;
  validRefs?: Set<string>;          // refs the backend verified; others are flagged
  onCite?: (ref: string) => void;   // click on a citation chip
}

type Block = { kind: "p" | "ol" | "ul"; items: string[] };

const normRef = (r: string) => r.replace(/\s*§\s*/, " §");

/** Line-based parse: list items start with "1." or "-"; indented lines after an item continue it;
 *  an unindented line after a list starts a new paragraph; blank lines end a block. */
function parse(text: string): Block[] {
  const blocks: Block[] = [];
  let cur: Block | null = null;
  for (const raw of text.replace(/\r/g, "").split("\n")) {
    const line = raw.trim();
    if (!line) { cur = null; continue; }
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

/** Minimal, safe Markdown: paragraphs, numbered and bulleted lists, **bold**, and [DOC §n] citations.
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
        const items = b.items.map((it, i) => <li key={i}>{inline(it, `${bi}-${i}`)}</li>);
        return b.kind === "ol" ? <ol key={bi}>{items}</ol> : <ul key={bi}>{items}</ul>;
      })}
    </div>
  );
}
