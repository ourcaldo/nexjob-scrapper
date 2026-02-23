"""
Content cleaning module for HTML job descriptions.
"""

import re
import html
from bs4 import BeautifulSoup
from typing import Set

# Matches ordered list items: "1.", "2)", "10." etc.
_ORDERED_LINE_RE = re.compile(r'^\d+[.)\s]')
# Matches unordered list items: "-", "•", "*"
_BULLET_CHARS = ("-", "•", "*")


class ContentCleaner:
    """Cleans and formats HTML content from job postings."""
    
    @staticmethod
    def clean_html(raw_html: str) -> str:
        """
        Cleans and formats HTML content from job postings.
        Used for JobStreet and other sources that need HTML processing.
        
        Args:
            raw_html: Raw HTML string from job posting
            
        Returns:
            Cleaned and formatted HTML string
        """
        if not raw_html:
            return ""
            
        soup = BeautifulSoup(html.unescape(raw_html), "html.parser")

        # Convert all h4 tags to h2 for consistency
        for h4 in soup.find_all("h4"):
            h4.name = "h2"

        output = []
        seen: Set[str] = set()

        for tag in soup.find_all(["h2", "p", "div", "ol", "ul"]):
            if tag.name == "h2":
                text = tag.get_text().strip()
                if text and text not in seen:
                    output.append(f"<h2>{text}</h2>")
                    seen.add(text)

            elif tag.name in ["ol", "ul"]:
                # Handle ordered and unordered lists
                list_items = tag.find_all("li", recursive=False)
                if list_items:
                    list_html = f"<{tag.name}>"
                    for li in list_items:
                        item_text = li.get_text().strip()
                        if item_text:
                            list_html += f"<li>{item_text}</li>"
                    list_html += f"</{tag.name}>"
                    
                    if list_html not in seen:
                        output.append(list_html)
                        seen.add(list_html)

            elif tag.name in ["p", "div"]:
                text = tag.get_text(separator="\n").strip()
                if not text:
                    continue

                lines = [line.strip() for line in text.splitlines() if line.strip()]

                # Require at least 2 lines and a consistent pattern to be treated as a list.
                # Ordered: every line must start with a digit followed by . or ) or space
                # Unordered: every line must start with a recognised bullet character
                is_ordered = (
                    len(lines) >= 2
                    and all(_ORDERED_LINE_RE.match(line) for line in lines)
                )
                is_unordered = (
                    len(lines) >= 2
                    and all(line.lstrip().startswith(_BULLET_CHARS) for line in lines)
                )

                # Format lists properly
                block = ""
                if is_ordered:
                    block = "<ol>" + "".join(
                        f"<li>{_ORDERED_LINE_RE.sub('', line).strip()}</li>"
                        for line in lines
                    ) + "</ol>"
                elif is_unordered:
                    block = "<ul>" + "".join(
                        f"<li>{line.lstrip('-•* ').strip()}</li>"
                        for line in lines
                    ) + "</ul>"
                else:
                    block = f"<p>{' '.join(lines)}</p>" if lines else ""

                if block and block not in seen:
                    output.append(block)
                    seen.add(block)

        return "\n".join(output).strip()
