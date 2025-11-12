"""
Content cleaning module for HTML job descriptions.
"""

import html
from bs4 import BeautifulSoup
from typing import Set


class ContentCleaner:
    """Cleans and formats HTML content from job postings."""
    
    @staticmethod
    def clean_html(raw_html: str) -> str:
        """
        Cleans and formats HTML content from job postings.
        
        Args:
            raw_html: Raw HTML string from job posting
            
        Returns:
            Cleaned and formatted HTML string
        """
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
                is_numbered = all(
                    line[:1].isdigit() or line.lstrip().startswith(("-", "•")) for line in lines
                )

                # Format lists properly
                block = ""
                if is_numbered and len(lines) >= 2:
                    if lines[0].startswith("1."):
                        block = "<ol>" + "".join(
                            f"<li>{line.lstrip('1234567890. ').strip()}</li>"
                            for line in lines
                        ) + "</ol>"
                    else:
                        block = "<ul>" + "".join(
                            f"<li>{line.lstrip('-• ').strip()}</li>"
                            for line in lines
                        ) + "</ul>"
                else:
                    block = f"<p>{' '.join(lines)}</p>" if lines else ""

                if block and block not in seen:
                    output.append(block)
                    seen.add(block)

        return "\n".join(output).strip()
