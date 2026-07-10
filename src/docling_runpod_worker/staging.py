from __future__ import annotations

from docling_core.types.doc.document import DocItemLabel, TableData, TableItem


def get_first_alpha_char(text: str) -> str | None:
    for char in text or "":
        if char.isalpha():
            return char
    return None


def should_merge_paragraphs(current_text: str, next_text: str) -> bool:
    if not current_text or not next_text:
        return False

    current_text = current_text.strip()
    next_text = next_text.strip()
    if not current_text or not next_text:
        return False

    sentence_endings = {".", "!", "?", ":", ";", "...", "…"}
    ends_with_punctuation = any(current_text.endswith(punct) for punct in sentence_endings)

    first_alpha = get_first_alpha_char(next_text)
    if first_alpha is None:
        return False

    return (not ends_with_punctuation) and (not first_alpha.isupper())


def page_marker(page_number: int) -> str:
    """Whitespace-delimited page provenance token for downstream chunkers."""
    return f" <page_number>{page_number}</page_number> "


def inject_page_markers(page_texts: list[str]) -> str:
    """Prefix non-empty page texts with markers.

    Page numbers are 1-based from the list index. Empty pages are skipped
    without shifting subsequent page numbers. Returns empty string (no markers)
    when every page is empty or page_texts is empty.
    """
    parts: list[str] = []
    for index, text in enumerate(page_texts):
        if not text or not str(text).strip():
            continue
        parts.append(f"{page_marker(index + 1)}{str(text).strip()}")
    return "\n\n".join(parts)


def stage_doc_docling(doc, output_path: str, margin: float = 2.0) -> int:
    pages = getattr(doc, "pages", None)
    if not pages:
        with open(output_path, "w", encoding="utf-8") as handle:
            handle.write("")
        return 0

    unique_header_areas = set()

    for page in pages:
        if not page.assembled or not page.assembled.elements:
            continue

        for element in page.assembled.elements:
            if element.label != DocItemLabel.PAGE_HEADER:
                continue
            if not element.cluster or not element.cluster.bbox:
                continue

            bbox = element.cluster.bbox
            unique_header_areas.add(
                (bbox.t - margin, bbox.b + margin, bbox.l - margin, bbox.r + margin)
            )

    for page in pages:
        if not page.assembled or not page.assembled.elements:
            continue

        for element in page.assembled.elements:
            if element.label == DocItemLabel.PAGE_HEADER:
                continue
            if not element.cluster or not element.cluster.bbox:
                continue

            bbox = element.cluster.bbox
            for area in unique_header_areas:
                target_top, target_bottom, target_left, target_right = area
                is_inside = (
                    bbox.t >= target_top
                    and bbox.b <= target_bottom
                    and bbox.l >= target_left
                    and bbox.r <= target_right
                )
                if is_inside:
                    element.label = DocItemLabel.PAGE_HEADER
                    if element.cluster:
                        element.cluster.label = DocItemLabel.PAGE_HEADER
                    break

    table_count = 0
    page_texts: list[str] = []

    for page in pages:
        chunks: list[str] = []

        if not page.assembled or not page.assembled.elements:
            page_texts.append("")
            continue

        elements = list(page.assembled.elements)
        previous_label = None
        index = 0

        while index < len(elements):
            element = elements[index]

            if previous_label == DocItemLabel.LIST_ITEM and element.label != DocItemLabel.LIST_ITEM:
                chunks.append("\n\n")

            if element.label == DocItemLabel.SECTION_HEADER:
                chunks.append(f"## {element.text}\n")
            elif element.label in {DocItemLabel.TABLE, DocItemLabel.DOCUMENT_INDEX}:
                table_data = TableData(
                    table_cells=element.table_cells,
                    num_rows=element.num_rows,
                    num_cols=element.num_cols,
                )
                table_item = TableItem(
                    data=table_data,
                    label=element.label,
                    self_ref=f"#/tables/{table_count}",
                    parent=None,
                    annotations=[],
                )
                markdown_table = table_item.export_to_markdown(
                    doc={
                        "schema_name": doc.document.schema_name,
                        "version": doc.document.version,
                        "name": doc.document.name,
                        "origin": None,
                    }
                )
                chunks.append(markdown_table)
                chunks.append("\n\n\n")
                table_count += 1
            elif element.label == DocItemLabel.KEY_VALUE_REGION:
                for cell in element.cluster.cells:
                    chunks.append(f"{cell.text}\n")
                chunks.append("\n\n")
            elif element.label == DocItemLabel.TEXT:
                merged_text = element.text
                while index + 1 < len(elements):
                    next_element = elements[index + 1]
                    if next_element.label != DocItemLabel.TEXT:
                        break
                    if not should_merge_paragraphs(merged_text, next_element.text):
                        break
                    merged_text = merged_text.strip() + " " + next_element.text.strip()
                    index += 1
                chunks.append(f"{merged_text}\n\n\n")
            elif element.label in {DocItemLabel.CAPTION, DocItemLabel.FOOTNOTE}:
                chunks.append(f"{element.text}\n\n\n")
            elif element.label == DocItemLabel.LIST_ITEM:
                chunks.append(f"{element.text}\n")

            previous_label = element.label
            index += 1

        if previous_label == DocItemLabel.LIST_ITEM:
            chunks.append("\n\n")

        page_texts.append("".join(chunks))

    with open(output_path, "w", encoding="utf-8") as handle:
        handle.write(inject_page_markers(page_texts))

    return table_count
