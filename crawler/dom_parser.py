"""
DOM parser for extracting structured information from web pages
"""

import logging
from typing import Dict, Any, List, Optional
from bs4 import BeautifulSoup, Tag, NavigableString
import re

class DOMParser:
    """Parser for extracting structured data from DOM"""
    
    def __init__(self):
        self.semantic_tags = {
            'header', 'nav', 'main', 'section', 'article', 'aside', 'footer',
            'h1', 'h2', 'h3', 'h4', 'h5', 'h6', 'p', 'div', 'span'
        }
        
        self.interactive_tags = {
            'a', 'button', 'input', 'select', 'textarea', 'form', 'label'
        }
        
        self.content_tags = {
            'img', 'video', 'audio', 'canvas', 'svg', 'table', 'ul', 'ol', 'dl'
        }
    
    def parse_page_structure(self, soup: BeautifulSoup) -> Dict[str, Any]:
        """Parse overall page structure"""
        try:
            structure = {
                'title': self.extract_title(soup),
                'meta_info': self.extract_meta_info(soup),
                'sections': self.extract_sections(soup),
                'semantic_structure': self.extract_semantic_structure(soup),
                'interactive_elements': self.extract_interactive_elements(soup),
                'content_blocks': self.extract_content_blocks(soup),
                'page_hierarchy': self.extract_page_hierarchy(soup)
            }
            
            return structure
            
        except Exception as e:
            logging.error(f"Error parsing page structure: {e}")
            return {}
    
    def extract_title(self, soup: BeautifulSoup) -> str:
        """Extract page title"""
        title_tag = soup.find('title')
        return title_tag.get_text().strip() if title_tag else ''
    
    def extract_meta_info(self, soup: BeautifulSoup) -> Dict[str, Any]:
        """Extract meta information"""
        meta_info = {
            'description': '',
            'keywords': '',
            'author': '',
            'viewport': '',
            'charset': '',
            'lang': ''
        }
        
        try:
            # Meta description
            desc_meta = soup.find('meta', attrs={'name': 'description'})
            if desc_meta:
                meta_info['description'] = desc_meta.get('content', '')
            
            # Meta keywords
            keywords_meta = soup.find('meta', attrs={'name': 'keywords'})
            if keywords_meta:
                meta_info['keywords'] = keywords_meta.get('content', '')
            
            # Author
            author_meta = soup.find('meta', attrs={'name': 'author'})
            if author_meta:
                meta_info['author'] = author_meta.get('content', '')
            
            # Viewport
            viewport_meta = soup.find('meta', attrs={'name': 'viewport'})
            if viewport_meta:
                meta_info['viewport'] = viewport_meta.get('content', '')
            
            # Charset
            charset_meta = soup.find('meta', attrs={'charset': True})
            if charset_meta:
                meta_info['charset'] = charset_meta.get('charset', '')
            
            # Language
            html_tag = soup.find('html')
            if html_tag:
                meta_info['lang'] = html_tag.get('lang', '')
                
        except Exception as e:
            logging.debug(f"Error extracting meta info: {e}")
        
        return meta_info
    
    def extract_sections(self, soup: BeautifulSoup) -> List[Dict[str, Any]]:
        """Extract main page sections"""
        sections = []
        
        try:
            # Find semantic sections
            section_selectors = [
                'header', 'nav', 'main', 'section', 'article', 'aside', 'footer'
            ]
            
            for selector in section_selectors:
                elements = soup.find_all(selector)
                for element in elements:
                    section_data = self.extract_element_info(element)
                    section_data['type'] = 'semantic_section'
                    section_data['tag'] = selector
                    sections.append(section_data)
            
            # Find sections by class/id patterns
            section_patterns = [
                r'header', r'nav', r'menu', r'sidebar', r'content', r'main',
                r'footer', r'banner', r'toolbar', r'panel'
            ]
            
            for pattern in section_patterns:
                elements = soup.find_all(attrs={'class': re.compile(pattern, re.I)})
                elements.extend(soup.find_all(attrs={'id': re.compile(pattern, re.I)}))
                
                for element in elements:
                    if element.name not in section_selectors:  # Avoid duplicates
                        section_data = self.extract_element_info(element)
                        section_data['type'] = 'pattern_section'
                        section_data['pattern'] = pattern
                        sections.append(section_data)
                        
        except Exception as e:
            logging.debug(f"Error extracting sections: {e}")
        
        return sections
    
    def extract_semantic_structure(self, soup: BeautifulSoup) -> Dict[str, Any]:
        """Extract semantic HTML5 structure"""
        structure = {
            'has_header': bool(soup.find('header')),
            'has_nav': bool(soup.find('nav')),
            'has_main': bool(soup.find('main')),
            'has_footer': bool(soup.find('footer')),
            'has_article': bool(soup.find('article')),
            'has_section': bool(soup.find('section')),
            'has_aside': bool(soup.find('aside')),
            'heading_structure': self.extract_heading_structure(soup),
            'landmark_roles': self.extract_landmark_roles(soup)
        }
        
        return structure
    
    def extract_heading_structure(self, soup: BeautifulSoup) -> List[Dict[str, Any]]:
        """Extract heading hierarchy"""
        headings = []
        
        try:
            heading_tags = soup.find_all(['h1', 'h2', 'h3', 'h4', 'h5', 'h6'])
            
            for heading in heading_tags:
                heading_data = {
                    'level': int(heading.name[1]),
                    'text': heading.get_text().strip(),
                    'id': heading.get('id', ''),
                    'class': heading.get('class', []),
                    'position': len(headings)
                }
                headings.append(heading_data)
                
        except Exception as e:
            logging.debug(f"Error extracting heading structure: {e}")
        
        return headings
    
    def extract_landmark_roles(self, soup: BeautifulSoup) -> List[Dict[str, Any]]:
        """Extract ARIA landmark roles"""
        landmarks = []
        
        try:
            landmark_roles = [
                'banner', 'navigation', 'main', 'complementary', 
                'contentinfo', 'form', 'search', 'region'
            ]
            
            for role in landmark_roles:
                elements = soup.find_all(attrs={'role': role})
                for element in elements:
                    landmark_data = {
                        'role': role,
                        'tag': element.name,
                        'aria_label': element.get('aria-label', ''),
                        'aria_labelledby': element.get('aria-labelledby', ''),
                        'id': element.get('id', ''),
                        'text_preview': element.get_text()[:100].strip()
                    }
                    landmarks.append(landmark_data)
                    
        except Exception as e:
            logging.debug(f"Error extracting landmark roles: {e}")
        
        return landmarks
    
    def extract_interactive_elements(self, soup: BeautifulSoup) -> List[Dict[str, Any]]:
        """Extract interactive elements for test generation"""
        interactive_elements = []
        
        try:
            # Buttons
            buttons = soup.find_all(['button', 'input[type="button"]', 'input[type="submit"]'])
            buttons.extend(soup.find_all(attrs={'role': 'button'}))
            
            for button in buttons:
                element_data = self.extract_element_info(button)
                element_data['element_type'] = 'button'
                element_data['clickable'] = True
                interactive_elements.append(element_data)
            
            # Links
            links = soup.find_all('a', href=True)
            for link in links:
                element_data = self.extract_element_info(link)
                element_data['element_type'] = 'link'
                element_data['href'] = link.get('href', '')
                element_data['clickable'] = True
                interactive_elements.append(element_data)
            
            # Form inputs
            inputs = soup.find_all(['input', 'textarea', 'select'])
            for input_elem in inputs:
                element_data = self.extract_element_info(input_elem)
                element_data['element_type'] = 'input'
                element_data['input_type'] = input_elem.get('type', input_elem.name)
                element_data['name'] = input_elem.get('name', '')
                element_data['required'] = input_elem.has_attr('required')
                element_data['fillable'] = True
                interactive_elements.append(element_data)
            
            # Form elements
            forms = soup.find_all('form')
            for form in forms:
                element_data = self.extract_element_info(form)
                element_data['element_type'] = 'form'
                element_data['action'] = form.get('action', '')
                element_data['method'] = form.get('method', 'get')
                element_data['submittable'] = True
                interactive_elements.append(element_data)
                
        except Exception as e:
            logging.debug(f"Error extracting interactive elements: {e}")
        
        return interactive_elements
    
    def extract_content_blocks(self, soup: BeautifulSoup) -> List[Dict[str, Any]]:
        """Extract content blocks for comprehension"""
        content_blocks = []
        
        try:
            # Text content blocks
            text_elements = soup.find_all(['p', 'div', 'span', 'article', 'section'])
            
            for element in text_elements:
                text_content = element.get_text().strip()
                if len(text_content) > 20:  # Only meaningful text blocks
                    block_data = {
                        'type': 'text_block',
                        'tag': element.name,
                        'text': text_content[:500],  # Limit text length
                        'text_length': len(text_content),
                        'id': element.get('id', ''),
                        'class': element.get('class', []),
                        'has_links': bool(element.find('a')),
                        'has_images': bool(element.find('img'))
                    }
                    content_blocks.append(block_data)
            
            # Tables
            tables = soup.find_all('table')
            for table in tables:
                table_data = self.extract_table_info(table)
                table_data['type'] = 'table'
                content_blocks.append(table_data)
            
            # Lists
            lists = soup.find_all(['ul', 'ol', 'dl'])
            for list_elem in lists:
                list_data = self.extract_list_info(list_elem)
                list_data['type'] = 'list'
                content_blocks.append(list_data)
            
            # Images
            images = soup.find_all('img')
            for img in images:
                img_data = {
                    'type': 'image',
                    'src': img.get('src', ''),
                    'alt': img.get('alt', ''),
                    'title': img.get('title', ''),
                    'width': img.get('width', ''),
                    'height': img.get('height', ''),
                    'id': img.get('id', ''),
                    'class': img.get('class', [])
                }
                content_blocks.append(img_data)
                
        except Exception as e:
            logging.debug(f"Error extracting content blocks: {e}")
        
        return content_blocks
    
    def extract_page_hierarchy(self, soup: BeautifulSoup) -> Dict[str, Any]:
        """Extract page hierarchy for navigation understanding"""
        hierarchy = {
            'depth': 0,
            'main_sections': [],
            'navigation_paths': [],
            'content_areas': []
        }
        
        try:
            # Calculate nesting depth
            hierarchy['depth'] = self.calculate_max_depth(soup.find('body') or soup)
            
            # Identify main sections
            main_sections = soup.find_all(['main', 'section', 'article'])
            for section in main_sections:
                section_info = {
                    'tag': section.name,
                    'id': section.get('id', ''),
                    'class': section.get('class', []),
                    'heading': self.find_section_heading(section),
                    'subsections': len(section.find_all(['section', 'article']))
                }
                hierarchy['main_sections'].append(section_info)
            
            # Extract navigation paths
            nav_elements = soup.find_all(['nav', 'menu'])
            nav_elements.extend(soup.find_all(attrs={'role': 'navigation'}))
            
            for nav in nav_elements:
                nav_info = {
                    'type': nav.name,
                    'id': nav.get('id', ''),
                    'class': nav.get('class', []),
                    'links': [{'text': link.get_text().strip(), 'href': link.get('href', '')} 
                             for link in nav.find_all('a', href=True)]
                }
                hierarchy['navigation_paths'].append(nav_info)
                
        except Exception as e:
            logging.debug(f"Error extracting page hierarchy: {e}")
        
        return hierarchy
    
    def extract_element_info(self, element: Tag) -> Dict[str, Any]:
        """Extract comprehensive information about an element"""
        return {
            'tag': element.name,
            'id': element.get('id', ''),
            'class': element.get('class', []),
            'text': element.get_text().strip()[:200],  # Limit text length
            'attributes': dict(element.attrs),
            'aria_label': element.get('aria-label', ''),
            'aria_role': element.get('role', ''),
            'title': element.get('title', ''),
            'data_attributes': {k: v for k, v in element.attrs.items() if k.startswith('data-')},
            'parent_tag': element.parent.name if element.parent else '',
            'child_count': len(element.find_all()),
            'text_length': len(element.get_text())
        }
    
    def extract_table_info(self, table: Tag) -> Dict[str, Any]:
        """Extract table structure information"""
        table_data = {
            'tag': 'table',
            'id': table.get('id', ''),
            'class': table.get('class', []),
            'caption': '',
            'headers': [],
            'row_count': 0,
            'column_count': 0,
            'has_thead': bool(table.find('thead')),
            'has_tbody': bool(table.find('tbody')),
            'has_tfoot': bool(table.find('tfoot'))
        }
        
        try:
            # Caption
            caption = table.find('caption')
            if caption:
                table_data['caption'] = caption.get_text().strip()
            
            # Headers
            header_cells = table.find_all(['th'])
            table_data['headers'] = [th.get_text().strip() for th in header_cells]
            
            # Row and column count
            rows = table.find_all('tr')
            table_data['row_count'] = len(rows)
            
            if rows:
                first_row = rows[0]
                cells = first_row.find_all(['td', 'th'])
                table_data['column_count'] = len(cells)
                
        except Exception as e:
            logging.debug(f"Error extracting table info: {e}")
        
        return table_data
    
    def extract_list_info(self, list_elem: Tag) -> Dict[str, Any]:
        """Extract list structure information"""
        list_data = {
            'tag': list_elem.name,
            'id': list_elem.get('id', ''),
            'class': list_elem.get('class', []),
            'list_type': list_elem.name,
            'item_count': 0,
            'items': [],
            'nested_lists': 0
        }
        
        try:
            # List items
            items = list_elem.find_all('li', recursive=False)  # Direct children only
            list_data['item_count'] = len(items)
            
            for item in items[:5]:  # Limit to first 5 items
                item_text = item.get_text().strip()
                list_data['items'].append(item_text[:100])  # Limit text length
            
            # Nested lists
            nested = list_elem.find_all(['ul', 'ol', 'dl'])
            list_data['nested_lists'] = len(nested)
            
        except Exception as e:
            logging.debug(f"Error extracting list info: {e}")
        
        return list_data
    
    def calculate_max_depth(self, element: Tag, current_depth: int = 0) -> int:
        """Calculate maximum nesting depth of elements"""
        if not isinstance(element, Tag):
            return current_depth
        
        max_child_depth = current_depth
        
        for child in element.children:
            if isinstance(child, Tag):
                child_depth = self.calculate_max_depth(child, current_depth + 1)
                max_child_depth = max(max_child_depth, child_depth)
        
        return max_child_depth
    
    def find_section_heading(self, section: Tag) -> str:
        """Find the main heading for a section"""
        try:
            # Look for heading tags
            heading = section.find(['h1', 'h2', 'h3', 'h4', 'h5', 'h6'])
            if heading:
                return heading.get_text().strip()
            
            # Look for aria-labelledby
            labelledby = section.get('aria-labelledby')
            if labelledby:
                label_element = section.find(id=labelledby)
                if label_element:
                    return label_element.get_text().strip()
            
            # Look for aria-label
            aria_label = section.get('aria-label')
            if aria_label:
                return aria_label
            
            return ''
            
        except Exception as e:
            logging.debug(f"Error finding section heading: {e}")
            return ''
    
    def generate_element_description(self, element_data: Dict[str, Any]) -> str:
        """Generate natural language description of an element"""
        try:
            tag = element_data.get('tag', '')
            element_type = element_data.get('element_type', tag)
            text = element_data.get('text', '').strip()
            id_attr = element_data.get('id', '')
            class_attr = element_data.get('class', [])
            aria_label = element_data.get('aria_label', '')
            
            # Start with element type
            description = f"{element_type}"
            
            # Add identifier information
            if aria_label:
                description += f" labeled '{aria_label}'"
            elif text and len(text) < 50:
                description += f" with text '{text}'"
            elif id_attr:
                description += f" with id '{id_attr}'"
            elif class_attr and isinstance(class_attr, list) and class_attr:
                description += f" with class '{' '.join(class_attr[:2])}'"
            
            # Add behavioral information
            if element_data.get('clickable'):
                description += " (clickable)"
            elif element_data.get('fillable'):
                description += " (fillable)"
            elif element_data.get('submittable'):
                description += " (submittable)"
            
            return description
            
        except Exception as e:
            logging.debug(f"Error generating element description: {e}")
            return f"{element_data.get('tag', 'element')}"
