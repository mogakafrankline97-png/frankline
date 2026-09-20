from fpdf import FPDF
import os
import textwrap
import uuid
import re
import tempfile
import shutil

def clean_text(text):
    if not text:
        return ""
    replacements = {
        '\u2013': '-', '\u2014': '-', '\u2018': "'", '\u2019': "'",
        '\u201c': '"', '\u201d': '"', '\u2022': '-', '\u2026': '...',
        '\u00a0': ' ', '\u00e9': 'e', '\u00e8': 'e', '\u00e0': 'a',
        '\u00f4': 'o', '\u00ee': 'i',
    }
    for old, new in replacements.items():
        text = text.replace(old, new)
    text = re.sub(r'[^\x00-\x7F]+', ' ', text)
    text = re.sub(r'\s+', ' ', text)
    return text.strip()

def create_cv_from_dict(data, layout='classic'):
    
    cleaned_data = {}
    for key, value in data.items():
        if isinstance(value, str):
            cleaned_data[key] = clean_text(value)
        elif isinstance(value, list):
            cleaned_data[key] = [clean_text(item) if isinstance(item, str) else item for item in value]
        else:
            cleaned_data[key] = value
    
    if layout == 'modern':
        return create_modern_cv(cleaned_data)
    else:
        return create_classic_cv(cleaned_data)


def create_classic_cv(data):
    class ClassicCV(FPDF):
        def __init__(self):
            super().__init__()
            self.set_auto_page_break(auto=True, margin=12)
            self.primary = (26, 35, 85)
            self.accent = (41, 128, 185)
            self.text_dark = (33, 33, 33)
            self.text_light = (117, 117, 117)
            self.sidebar_bg = (248, 249, 252)
            self.gold = (184, 134, 11)
            self.sidebar_width = 48
            self.main_x = 62
            self.main_width = 135
        
        def set_color(self, r, g, b):
            self.set_text_color(int(r), int(g), int(b))
        
        def set_fill(self, r, g, b):
            self.set_fill_color(int(r), int(g), int(b))
        
        def set_draw(self, r, g, b):
            self.set_draw_color(int(r), int(g), int(b))
        
        def add_sidebar(self, name, title, contact_info, skills, languages):
            page_height = 297
            sw = self.sidebar_width
            
            self.set_fill(self.sidebar_bg[0], self.sidebar_bg[1], self.sidebar_bg[2])
            self.rect(0, 0, sw, page_height, 'F')
            
            self.set_fill(self.primary[0], self.primary[1], self.primary[2])
            self.rect(0, 0, 210, 4, 'F')
            self.rect(0, page_height - 4, 210, 4, 'F')
            
            name_clean = clean_text(name) if name else "CURRICULUM VITAE"
            self.set_xy(6, 15)
            self.set_color(self.primary[0], self.primary[1], self.primary[2])
            self.set_font("Helvetica", "B", 9)
            self.multi_cell(sw - 12, 3.5, name_clean.upper(), 0, 'C')
            
            if title:
                self.set_xy(6, 30)
                self.set_color(self.accent[0], self.accent[1], self.accent[2])
                self.set_font("Helvetica", "B", 5.5)
                self.cell(sw - 12, 2.5, clean_text(title), 0, 1, 'C')
                self.set_draw(self.accent[0], self.accent[1], self.accent[2])
                self.line(14, 34, sw - 14, 34)
            
            y_pos = 42
            self.set_xy(8, y_pos)
            self.set_color(self.primary[0], self.primary[1], self.primary[2])
            self.set_font("Helvetica", "B", 5.5)
            self.cell(sw - 16, 2.5, "CONTACT", 0, 1, 'L')
            self.set_draw(self.accent[0], self.accent[1], self.accent[2])
            self.line(8, y_pos + 3.5, sw - 8, y_pos + 3.5)
            
            y_pos += 6
            if contact_info.get('email'):
                self.set_xy(10, y_pos)
                self.set_color(self.text_dark[0], self.text_dark[1], self.text_dark[2])
                self.set_font("Helvetica", "", 4.5)
                email_clean = clean_text(str(contact_info['email']))
                wrapped_email = textwrap.fill(email_clean, width=16)
                self.multi_cell(sw - 20, 2, wrapped_email, 0, 'L')
                y_pos += len(wrapped_email.split('\n')) * 2 + 3
            
            if contact_info.get('phone'):
                self.set_xy(10, y_pos)
                self.set_color(self.text_dark[0], self.text_dark[1], self.text_dark[2])
                self.set_font("Helvetica", "", 4.5)
                self.cell(sw - 20, 2, clean_text(str(contact_info['phone'])), 0, 1, 'L')
                y_pos += 3
            
            if skills:
                y_pos += 2
                if y_pos < 250:
                    self.set_xy(8, y_pos)
                    self.set_color(self.primary[0], self.primary[1], self.primary[2])
                    self.set_font("Helvetica", "B", 5.5)
                    self.cell(sw - 16, 2.5, "SKILLS", 0, 1, 'L')
                    self.set_draw(self.accent[0], self.accent[1], self.accent[2])
                    self.line(8, y_pos + 3.5, sw - 8, y_pos + 3.5)
                    
                    y_pos += 6
                    for skill in skills[:10]:
                        if y_pos > 250:
                            break
                        self.set_xy(10, y_pos)
                        self.set_color(self.accent[0], self.accent[1], self.accent[2])
                        self.set_font("Helvetica", "", 4.5)
                        self.cell(2, 2, "-", 0, 0, 'L')
                        self.set_color(self.text_dark[0], self.text_dark[1], self.text_dark[2])
                        self.set_font("Helvetica", "", 4.5)
                        skill_clean = clean_text(skill)
                        wrapped_skill = textwrap.fill(skill_clean, width=14)
                        self.multi_cell(sw - 22, 2, wrapped_skill, 0, 'L')
                        y_pos += len(wrapped_skill.split('\n')) * 2 + 1
            
            languages = languages or ["English", "Swahili"]
            y_pos += 2
            if y_pos < 250:
                self.set_xy(8, y_pos)
                self.set_color(self.primary[0], self.primary[1], self.primary[2])
                self.set_font("Helvetica", "B", 5.5)
                self.cell(sw - 16, 2.5, "LANGUAGES", 0, 1, 'L')
                self.set_draw(self.accent[0], self.accent[1], self.accent[2])
                self.line(8, y_pos + 3.5, sw - 8, y_pos + 3.5)
                
                y_pos += 6
                for lang in languages[:3]:
                    if y_pos > 250:
                        break
                    self.set_xy(10, y_pos)
                    self.set_color(self.accent[0], self.accent[1], self.accent[2])
                    self.set_font("Helvetica", "", 4.5)
                    self.cell(2, 2, "-", 0, 0, 'L')
                    self.set_color(self.text_dark[0], self.text_dark[1], self.text_dark[2])
                    self.set_font("Helvetica", "", 4.5)
                    self.cell(sw - 22, 2, clean_text(lang), 0, 1, 'L')
                    y_pos += 2.5
            
            self.set_draw(self.primary[0], self.primary[1], self.primary[2])
            self.set_line_width(0.5)
            self.line(sw, 0, sw, page_height)
        
        def add_main_content(self, summary, experience, education, achievements, references):
            main_x = self.main_x
            main_width = self.main_width
            y_pos = 12
            
            name = data.get('name', 'CURRICULUM VITAE')
            self.set_xy(main_x, y_pos)
            self.set_color(self.primary[0], self.primary[1], self.primary[2])
            self.set_font("Helvetica", "B", 18)
            self.cell(main_width, 7, clean_text(name).upper(), 0, 1, 'L')
            y_pos += 7
            
            title = data.get('title', '')
            if title:
                self.set_xy(main_x, y_pos)
                self.set_color(self.accent[0], self.accent[1], self.accent[2])
                self.set_font("Helvetica", "B", 9)
                self.cell(main_width, 4, clean_text(title), 0, 1, 'L')
                y_pos += 5
            
            self.set_draw(self.gold[0], self.gold[1], self.gold[2])
            self.set_line_width(0.5)
            self.line(main_x, y_pos, main_x + 40, y_pos)
            y_pos += 6
            
            if summary:
                self.set_xy(main_x, y_pos)
                self.set_color(self.primary[0], self.primary[1], self.primary[2])
                self.set_font("Helvetica", "B", 7.5)
                self.cell(main_width, 3.5, "PROFESSIONAL SUMMARY", 0, 1, 'L')
                self.set_draw(self.accent[0], self.accent[1], self.accent[2])
                self.line(main_x, y_pos + 4.5, main_x + 35, y_pos + 4.5)
                y_pos += 6
                
                self.set_xy(main_x, y_pos)
                self.set_color(self.text_dark[0], self.text_dark[1], self.text_dark[2])
                self.set_font("Helvetica", "", 7)
                summary_clean = clean_text(summary)
                wrapped_summary = textwrap.fill(summary_clean, width=72)
                self.multi_cell(main_width, 3.5, wrapped_summary, 0, 'L')
                y_pos += len(wrapped_summary.split('\n')) * 3.5 + 5
            
            if education:
                self.set_xy(main_x, y_pos)
                self.set_color(self.primary[0], self.primary[1], self.primary[2])
                self.set_font("Helvetica", "B", 7.5)
                self.cell(main_width, 3.5, "EDUCATION", 0, 1, 'L')
                self.set_draw(self.accent[0], self.accent[1], self.accent[2])
                self.line(main_x, y_pos + 4.5, main_x + 25, y_pos + 4.5)
                y_pos += 6
                
                for edu in education[:4]:
                    if y_pos > 260:
                        self.add_page()
                        y_pos = 12
                    self.set_xy(main_x, y_pos)
                    self.set_color(self.text_dark[0], self.text_dark[1], self.text_dark[2])
                    self.set_font("Helvetica", "", 7)
                    self.cell(main_width, 3.5, clean_text(edu), 0, 1, 'L')
                    y_pos += 4
                y_pos += 2
            
            if experience:
                if y_pos > 240:
                    self.add_page()
                    y_pos = 12
                
                self.set_xy(main_x, y_pos)
                self.set_color(self.primary[0], self.primary[1], self.primary[2])
                self.set_font("Helvetica", "B", 7.5)
                self.cell(main_width, 3.5, "EMPLOYMENT", 0, 1, 'L')
                self.set_draw(self.accent[0], self.accent[1], self.accent[2])
                self.line(main_x, y_pos + 4.5, main_x + 28, y_pos + 4.5)
                y_pos += 6
                
                for idx, exp in enumerate(experience[:4]):
                    if y_pos > 245:
                        self.add_page()
                        y_pos = 12
                    
                    company = clean_text(exp.get('company', ''))
                    if company:
                        self.set_xy(main_x, y_pos)
                        self.set_color(self.primary[0], self.primary[1], self.primary[2])
                        self.set_font("Helvetica", "B", 7)
                        self.cell(main_width, 3.5, company, 0, 1, 'L')
                        y_pos += 3.5
                    
                    title_text = clean_text(exp.get('title', ''))
                    date_text = clean_text(exp.get('date', ''))
                    
                    if title_text or date_text:
                        self.set_xy(main_x, y_pos)
                        if title_text:
                            self.set_color(self.accent[0], self.accent[1], self.accent[2])
                            self.set_font("Helvetica", "B", 6.5)
                            self.cell(main_width * 0.5, 3, title_text, 0, 0, 'L')
                        if date_text:
                            self.set_color(self.text_light[0], self.text_light[1], self.text_light[2])
                            self.set_font("Helvetica", "I", 6)
                            self.cell(main_width * 0.5, 3, date_text, 0, 1, 'R')
                        y_pos += 3
                    
                    if exp.get('bullets'):
                        for bullet in exp['bullets'][:3]:
                            if y_pos > 260:
                                self.add_page()
                                y_pos = 12
                            bullet_clean = clean_text(bullet)
                            bullet_clean = re.sub(r'^[•\-]\s*', '', bullet_clean)
                            self.set_xy(main_x + 3, y_pos)
                            self.set_color(self.accent[0], self.accent[1], self.accent[2])
                            self.set_font("Helvetica", "", 5.5)
                            self.cell(2, 2.5, "-", 0, 0, 'L')
                            self.set_color(self.text_dark[0], self.text_dark[1], self.text_dark[2])
                            self.set_font("Helvetica", "", 5.5)
                            wrapped_bullet = textwrap.fill(bullet_clean, width=65)
                            self.multi_cell(main_width - 8, 2.5, wrapped_bullet, 0, 'L')
                            y_pos += len(wrapped_bullet.split('\n')) * 2.5 + 1
                    
                    if idx < len(experience[:4]) - 1:
                        y_pos += 2
                y_pos += 2
            
            if achievements:
                if y_pos > 240:
                    self.add_page()
                    y_pos = 12
                
                self.set_xy(main_x, y_pos)
                self.set_color(self.primary[0], self.primary[1], self.primary[2])
                self.set_font("Helvetica", "B", 7.5)
                self.cell(main_width, 3.5, "QUALIFICATIONS", 0, 1, 'L')
                self.set_draw(self.accent[0], self.accent[1], self.accent[2])
                self.line(main_x, y_pos + 4.5, main_x + 35, y_pos + 4.5)
                y_pos += 6
                
                for ach in achievements[:5]:
                    if y_pos > 260:
                        self.add_page()
                        y_pos = 12
                    ach_clean = clean_text(ach)
                    self.set_xy(main_x + 3, y_pos)
                    self.set_color(self.gold[0], self.gold[1], self.gold[2])
                    self.set_font("Helvetica", "", 5.5)
                    self.cell(2, 2.5, "+", 0, 0, 'L')
                    self.set_color(self.text_dark[0], self.text_dark[1], self.text_dark[2])
                    self.set_font("Helvetica", "", 5.5)
                    wrapped_ach = textwrap.fill(ach_clean, width=65)
                    self.multi_cell(main_width - 8, 2.5, wrapped_ach, 0, 'L')
                    y_pos += len(wrapped_ach.split('\n')) * 2.5 + 1
                y_pos += 2
            
            if references:
                if y_pos > 240:
                    self.add_page()
                    y_pos = 12
                
                self.set_xy(main_x, y_pos)
                self.set_color(self.primary[0], self.primary[1], self.primary[2])
                self.set_font("Helvetica", "B", 7.5)
                self.cell(main_width, 3.5, "REFERENCES", 0, 1, 'L')
                self.set_draw(self.accent[0], self.accent[1], self.accent[2])
                self.line(main_x, y_pos + 4.5, main_x + 30, y_pos + 4.5)
                y_pos += 6
                
                for ref in references[:3]:
                    if y_pos > 260:
                        self.add_page()
                        y_pos = 12
                    
                    ref_name = clean_text(ref.get('name', ''))
                    if ref_name:
                        self.set_xy(main_x, y_pos)
                        self.set_color(self.primary[0], self.primary[1], self.primary[2])
                        self.set_font("Helvetica", "B", 6.5)
                        self.cell(main_width, 3, ref_name, 0, 1, 'L')
                        y_pos += 3
                    
                    ref_pos = clean_text(ref.get('position', ''))
                    if ref_pos:
                        self.set_xy(main_x, y_pos)
                        self.set_color(self.text_dark[0], self.text_dark[1], self.text_dark[2])
                        self.set_font("Helvetica", "", 5.5)
                        self.cell(main_width, 2.5, ref_pos, 0, 1, 'L')
                        y_pos += 2.5
                    
                    ref_email = clean_text(ref.get('email', ''))
                    if ref_email:
                        self.set_xy(main_x, y_pos)
                        self.set_color(self.text_light[0], self.text_light[1], self.text_light[2])
                        self.set_font("Helvetica", "", 5)
                        self.cell(main_width, 2.5, ref_email, 0, 1, 'L')
                        y_pos += 2.5
                    
                    if ref != references[-1]:
                        y_pos += 2
        
        def add_page(self):
            super().add_page()
            page_height = 297
            sw = self.sidebar_width
            
            self.set_fill(self.sidebar_bg[0], self.sidebar_bg[1], self.sidebar_bg[2])
            self.rect(0, 0, sw, page_height, 'F')
            
            self.set_fill(self.primary[0], self.primary[1], self.primary[2])
            self.rect(0, 0, 210, 4, 'F')
            self.rect(0, page_height - 4, 210, 4, 'F')
            
            self.set_draw(self.primary[0], self.primary[1], self.primary[2])
            self.set_line_width(0.5)
            self.line(sw, 0, sw, page_height)
            
            name = data.get('name', 'CURRICULUM VITAE')
            self.set_xy(6, 15)
            self.set_color(self.primary[0], self.primary[1], self.primary[2])
            self.set_font("Helvetica", "B", 8)
            self.multi_cell(sw - 12, 3.5, clean_text(name), 0, 'C')
            
            self.set_xy(6, 28)
            self.set_color(self.text_light[0], self.text_light[1], self.text_light[2])
            self.set_font("Helvetica", "I", 5)
            self.cell(sw - 12, 2.5, f"Page {self.page_no()}", 0, 1, 'C')
    
    pdf = ClassicCV()
    pdf.add_page()
    
    name = data.get('name', 'CURRICULUM VITAE')
    title = data.get('title', '')
    
    contact_info = {}
    if data.get('email'):
        contact_info['email'] = clean_text(data['email'])
    if data.get('phone'):
        contact_info['phone'] = clean_text(data['phone'])
    
    skills = data.get('skills', [])
    if not skills:
        skills = ['No skills extracted']
    
    languages = ['English', 'Swahili']
    
    pdf.add_sidebar(name, title, contact_info, skills, languages)
    
    pdf.add_main_content(
        data.get('summary', ''),
        data.get('experience', []),
        data.get('education', []),
        data.get('achievements', []),
        data.get('references', [])
    )
    
    safe_name = re.sub(r'[^\x00-\x7F]+', '', name.replace(' ', '_')[:20]) if name else 'cv'
    filename = f"{safe_name}_{uuid.uuid4().hex[:8]}.pdf"
    
    temp_dir = tempfile.gettempdir()
    temp_path = os.path.join(temp_dir, filename)
    pdf.output(temp_path)
    
    try:
        if not os.path.exists('generated'):
            os.makedirs('generated')
        shutil.copy2(temp_path, os.path.join('generated', filename))
    except:
        pass
    
    return temp_path


def create_modern_cv(data):
    class ModernCV(FPDF):
        def __init__(self):
            super().__init__()
            self.set_auto_page_break(auto=True, margin=12)
            self.primary = (44, 62, 80)
            self.accent = (231, 76, 60)
            self.text_dark = (44, 62, 80)
            self.text_light = (127, 140, 141)
            self.white = (255, 255, 255)
            self.gold = (241, 196, 15)
            self.main_x = 15
            self.main_width = 180
        
        def set_color(self, r, g, b):
            self.set_text_color(int(r), int(g), int(b))
        
        def set_fill(self, r, g, b):
            self.set_fill_color(int(r), int(g), int(b))
        
        def set_draw(self, r, g, b):
            self.set_draw_color(int(r), int(g), int(b))
        
        def add_header(self, name, title, contact_info):
            self.set_fill(self.primary[0], self.primary[1], self.primary[2])
            self.rect(0, 0, 210, 38, 'F')
            
            self.set_xy(15, 8)
            self.set_color(self.white[0], self.white[1], self.white[2])
            self.set_font("Helvetica", "B", 20)
            self.cell(180, 8, clean_text(name).upper(), 0, 1, 'L')
            
            if title:
                self.set_xy(15, 18)
                self.set_color(self.accent[0], self.accent[1], self.accent[2])
                self.set_font("Helvetica", "B", 10)
                self.cell(180, 5, clean_text(title), 0, 1, 'L')
            
            self.set_xy(15, 26)
            self.set_color(self.white[0], self.white[1], self.white[2])
            self.set_font("Helvetica", "", 7)
            contact_text = ""
            if contact_info.get('email'):
                contact_text += f"Email: {contact_info['email']}  "
            if contact_info.get('phone'):
                contact_text += f"Phone: {contact_info['phone']}"
            self.cell(180, 4, contact_text, 0, 1, 'L')
            
            self.set_draw(self.accent[0], self.accent[1], self.accent[2])
            self.set_line_width(1.5)
            self.line(15, 34, 195, 34)
            
            return 42
        
        def add_section_title(self, title, y_pos):
            self.set_xy(self.main_x, y_pos)
            self.set_color(self.primary[0], self.primary[1], self.primary[2])
            self.set_font("Helvetica", "B", 10)
            self.cell(self.main_width, 5, title.upper(), 0, 1, 'L')
            self.set_draw(self.accent[0], self.accent[1], self.accent[2])
            self.set_line_width(0.3)
            self.line(self.main_x, y_pos + 5.5, self.main_x + 35, y_pos + 5.5)
            return y_pos + 8
        
        def add_main_content(self, summary, experience, education, achievements, references):
            y_pos = 42
            
            if summary:
                y_pos = self.add_section_title("PROFESSIONAL SUMMARY", y_pos)
                self.set_xy(self.main_x, y_pos)
                self.set_color(self.text_dark[0], self.text_dark[1], self.text_dark[2])
                self.set_font("Helvetica", "", 8)
                summary_clean = clean_text(summary)
                wrapped_summary = textwrap.fill(summary_clean, width=90)
                self.multi_cell(self.main_width, 4, wrapped_summary, 0, 'L')
                y_pos += len(wrapped_summary.split('\n')) * 4 + 6
            
            if experience:
                y_pos = self.add_section_title("WORK EXPERIENCE", y_pos)
                for exp in experience[:4]:
                    if y_pos > 260:
                        self.add_page()
                        y_pos = 42
                    
                    company = clean_text(exp.get('company', ''))
                    title_text = clean_text(exp.get('title', ''))
                    date_text = clean_text(exp.get('date', ''))
                    
                    self.set_xy(self.main_x, y_pos)
                    self.set_color(self.primary[0], self.primary[1], self.primary[2])
                    self.set_font("Helvetica", "B", 8.5)
                    self.cell(self.main_width * 0.6, 4.5, company, 0, 0, 'L')
                    self.set_color(self.text_light[0], self.text_light[1], self.text_light[2])
                    self.set_font("Helvetica", "I", 7.5)
                    self.cell(self.main_width * 0.4, 4.5, date_text, 0, 1, 'R')
                    y_pos += 4.5
                    
                    if title_text:
                        self.set_xy(self.main_x, y_pos)
                        self.set_color(self.accent[0], self.accent[1], self.accent[2])
                        self.set_font("Helvetica", "B", 8)
                        self.cell(self.main_width, 4, title_text, 0, 1, 'L')
                        y_pos += 4
                    
                    if exp.get('bullets'):
                        for bullet in exp['bullets'][:2]:
                            if y_pos > 260:
                                self.add_page()
                                y_pos = 42
                            bullet_clean = clean_text(bullet)
                            bullet_clean = re.sub(r'^[•\-]\s*', '', bullet_clean)
                            self.set_xy(self.main_x + 4, y_pos)
                            self.set_color(self.text_dark[0], self.text_dark[1], self.text_dark[2])
                            self.set_font("Helvetica", "", 7)
                            self.cell(3, 3.5, "-", 0, 0, 'L')
                            wrapped_bullet = textwrap.fill(bullet_clean, width=80)
                            self.multi_cell(self.main_width - 10, 3.5, wrapped_bullet, 0, 'L')
                            y_pos += len(wrapped_bullet.split('\n')) * 3.5 + 1
                    y_pos += 3
            
            if education:
                if y_pos > 240:
                    self.add_page()
                    y_pos = 42
                y_pos = self.add_section_title("EDUCATION", y_pos)
                for edu in education[:3]:
                    self.set_xy(self.main_x, y_pos)
                    self.set_color(self.text_dark[0], self.text_dark[1], self.text_dark[2])
                    self.set_font("Helvetica", "", 8)
                    self.cell(self.main_width, 4, clean_text(edu), 0, 1, 'L')
                    y_pos += 4.5
            
            if achievements:
                if y_pos > 240:
                    self.add_page()
                    y_pos = 42
                y_pos = self.add_section_title("ACHIEVEMENTS", y_pos)
                for ach in achievements[:3]:
                    ach_clean = clean_text(ach)
                    self.set_xy(self.main_x + 4, y_pos)
                    self.set_color(self.gold[0], self.gold[1], self.gold[2])
                    self.set_font("Helvetica", "", 7)
                    self.cell(3, 3.5, "*", 0, 0, 'L')
                    self.set_color(self.text_dark[0], self.text_dark[1], self.text_dark[2])
                    wrapped_ach = textwrap.fill(ach_clean, width=80)
                    self.multi_cell(self.main_width - 10, 3.5, wrapped_ach, 0, 'L')
                    y_pos += len(wrapped_ach.split('\n')) * 3.5 + 2
            
            if references:
                if y_pos > 240:
                    self.add_page()
                    y_pos = 42
                y_pos = self.add_section_title("REFERENCES", y_pos)
                for ref in references[:3]:
                    ref_name = clean_text(ref.get('name', ''))
                    if ref_name:
                        self.set_xy(self.main_x, y_pos)
                        self.set_color(self.text_dark[0], self.text_dark[1], self.text_dark[2])
                        self.set_font("Helvetica", "", 7.5)
                        self.cell(self.main_width, 3.5, ref_name, 0, 1, 'L')
                        y_pos += 3.5
                    
                    ref_email = clean_text(ref.get('email', ''))
                    if ref_email:
                        self.set_xy(self.main_x, y_pos)
                        self.set_color(self.text_light[0], self.text_light[1], self.text_light[2])
                        self.set_font("Helvetica", "", 6.5)
                        self.cell(self.main_width, 3, ref_email, 0, 1, 'L')
                        y_pos += 3
        
        def add_page(self):
            super().add_page()
            self.set_fill(self.primary[0], self.primary[1], self.primary[2])
            self.rect(0, 0, 210, 38, 'F')
            
            name = data.get('name', 'CURRICULUM VITAE')
            self.set_xy(15, 8)
            self.set_color(self.white[0], self.white[1], self.white[2])
            self.set_font("Helvetica", "B", 16)
            self.cell(180, 7, clean_text(name).upper(), 0, 1, 'L')
            self.set_xy(15, 20)
            self.set_color(self.white[0], self.white[1], self.white[2])
            self.set_font("Helvetica", "", 7)
            self.cell(180, 4, f"Page {self.page_no()}", 0, 1, 'R')
            
            self.set_draw(self.accent[0], self.accent[1], self.accent[2])
            self.set_line_width(1.5)
            self.line(15, 34, 195, 34)
    
    pdf = ModernCV()
    pdf.add_page()
    
    name = data.get('name', 'CURRICULUM VITAE')
    title = data.get('title', '')
    
    contact_info = {}
    if data.get('email'):
        contact_info['email'] = clean_text(data['email'])
    if data.get('phone'):
        contact_info['phone'] = clean_text(data['phone'])
    
    pdf.add_header(name, title, contact_info)
    
    pdf.add_main_content(
        data.get('summary', ''),
        data.get('experience', []),
        data.get('education', []),
        data.get('achievements', []),
        data.get('references', [])
    )
    
    safe_name = re.sub(r'[^\x00-\x7F]+', '', name.replace(' ', '_')[:20]) if name else 'cv'
    filename = f"{safe_name}_{uuid.uuid4().hex[:8]}.pdf"
    
    temp_dir = tempfile.gettempdir()
    temp_path = os.path.join(temp_dir, filename)
    pdf.output(temp_path)
    
    try:
        if not os.path.exists('generated'):
            os.makedirs('generated')
        shutil.copy2(temp_path, os.path.join('generated', filename))
    except:
        pass
    
    return temp_path
