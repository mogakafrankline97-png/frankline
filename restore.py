from fpdf import FPDF
import os
import textwrap

class PDF(FPDF):
    def __init__(self):
        super().__init__(orientation='P', unit='mm', format='A4')
        self.set_auto_page_break(auto=True, margin=15)
        self.set_margins(15, 15, 15)
        # Clean, consistent color scheme - Professional Blue Theme
        self.primary = (44, 62, 80)  # Dark slate blue
        self.secondary = (52, 73, 94)  # Medium slate
        self.accent = (41, 128, 185)  # Blue accent
        self.text_dark = (44, 62, 80)  # Dark slate
        self.text_light = (127, 140, 141)  # Gray
        self.sidebar_bg = (248, 249, 250)  # Very light gray
        self.white = (255, 255, 255)
        self.gold = (241, 196, 15)  # Gold accent
        self.sidebar_width = 55
        self.main_x = 70
        self.main_width = 125
    
    def set_color(self, r, g, b):
        self.set_text_color(int(r), int(g), int(b))
    
    def set_fill(self, r, g, b):
        self.set_fill_color(int(r), int(g), int(b))
    
    def set_draw(self, r, g, b):
        self.set_draw_color(int(r), int(g), int(b))
    
    def add_sidebar(self, name, title, contact_info, skills, languages, certifications, personal_info=None):
        page_height = 297
        sidebar_width = self.sidebar_width
        
        # Sidebar background
        self.set_fill(self.sidebar_bg[0], self.sidebar_bg[1], self.sidebar_bg[2])
        self.rect(0, 0, sidebar_width, page_height, 'F')
        
        # Decorative top bar
        self.set_fill(self.primary[0], self.primary[1], self.primary[2])
        self.rect(0, 0, 210, 8, 'F')
        
        # Bottom decorative bar
        self.set_fill(self.primary[0], self.primary[1], self.primary[2])
        self.rect(0, page_height - 8, 210, 8, 'F')
        
        # Name
        self.set_xy(8, 25)
        self.set_color(self.primary[0], self.primary[1], self.primary[2])
        self.set_font("Helvetica", "B", 11)
        self.multi_cell(sidebar_width - 16, 5, name.upper(), 0, 'C')
        
        # Title - TWO LINES
        self.set_xy(8, 44)
        self.set_color(self.accent[0], self.accent[1], self.accent[2])
        self.set_font("Helvetica", "B", 8)
        self.multi_cell(sidebar_width - 16, 4, "Education Professional", 0, 'C')
        
        self.set_xy(8, 52)
        self.set_color(self.accent[0], self.accent[1], self.accent[2])
        self.set_font("Helvetica", "B", 8)
        self.multi_cell(sidebar_width - 16, 4, "Inclusion Specialist", 0, 'C')
        
        # Decorative line
        self.set_draw(self.accent[0], self.accent[1], self.accent[2])
        self.set_line_width(0.5)
        self.line(18, 60, sidebar_width - 18, 60)
        
        # CONTACT section
        y_pos = 74
        self.set_xy(10, y_pos)
        self.set_color(self.primary[0], self.primary[1], self.primary[2])
        self.set_font("Helvetica", "B", 9)
        self.cell(sidebar_width - 20, 5, "CONTACT", 0, 1, 'L')
        self.set_draw(self.accent[0], self.accent[1], self.accent[2])
        self.set_line_width(0.3)
        self.line(10, y_pos + 6, sidebar_width - 10, y_pos + 6)
        
        # Contact details
        y_pos += 14
        details = [
            ("Address", contact_info["address"]),
            ("Phone", contact_info["phone"]),
            ("Email", contact_info["email"])
        ]
        
        for label, value in details:
            if y_pos > 250:
                break
            
            self.set_xy(12, y_pos)
            self.set_color(self.text_light[0], self.text_light[1], self.text_light[2])
            self.set_font("Helvetica", "B", 7)
            self.cell(12, 4, label + ":", 0, 0, 'L')
            
            self.set_color(self.text_dark[0], self.text_dark[1], self.text_dark[2])
            self.set_font("Helvetica", "", 7.5)
            self.set_xy(12, y_pos + 5)
            wrapped_value = textwrap.fill(value, width=18)
            self.multi_cell(sidebar_width - 24, 4, wrapped_value, 0, 'L')
            y_pos += len(wrapped_value.split('\n')) * 4 + 8
        
        # PERSONAL INFO
        if personal_info:
            y_pos += 2
            if y_pos < 250:
                self.set_xy(10, y_pos)
                self.set_color(self.primary[0], self.primary[1], self.primary[2])
                self.set_font("Helvetica", "B", 9)
                self.cell(sidebar_width - 20, 5, "PERSONAL INFO", 0, 1, 'L')
                self.set_draw(self.accent[0], self.accent[1], self.accent[2])
                self.set_line_width(0.3)
                self.line(10, y_pos + 6, sidebar_width - 10, y_pos + 6)
                
                y_pos += 14
                for label, value in personal_info.items():
                    if y_pos > 250:
                        break
                    self.set_xy(12, y_pos)
                    self.set_color(self.text_light[0], self.text_light[1], self.text_light[2])
                    self.set_font("Helvetica", "B", 7)
                    self.cell(12, 4, label + ":", 0, 0, 'L')
                    
                    self.set_color(self.text_dark[0], self.text_dark[1], self.text_dark[2])
                    self.set_font("Helvetica", "", 7.5)
                    self.set_xy(12, y_pos + 5)
                    self.multi_cell(sidebar_width - 24, 4, str(value), 0, 'L')
                    y_pos += 12
        
        # SKILLS section
        y_pos += 4
        if y_pos < 250:
            self.set_xy(10, y_pos)
            self.set_color(self.primary[0], self.primary[1], self.primary[2])
            self.set_font("Helvetica", "B", 9)
            self.cell(sidebar_width - 20, 5, "SKILLS", 0, 1, 'L')
            self.set_draw(self.accent[0], self.accent[1], self.accent[2])
            self.set_line_width(0.3)
            self.line(10, y_pos + 6, sidebar_width - 10, y_pos + 6)
            
            y_pos += 14
            for skill in skills:
                if y_pos > 250:
                    break
                self.set_xy(12, y_pos)
                self.set_color(self.accent[0], self.accent[1], self.accent[2])
                self.set_font("Helvetica", "", 8)
                self.cell(4, 4, "-", 0, 0, 'L')
                self.set_color(self.text_dark[0], self.text_dark[1], self.text_dark[2])
                self.set_font("Helvetica", "", 7.5)
                wrapped_skill = textwrap.fill(skill, width=18)
                self.multi_cell(sidebar_width - 24, 4, wrapped_skill, 0, 'L')
                y_pos += len(wrapped_skill.split('\n')) * 4 + 2
        
        # LANGUAGES section
        y_pos += 4
        if y_pos < 250:
            self.set_xy(10, y_pos)
            self.set_color(self.primary[0], self.primary[1], self.primary[2])
            self.set_font("Helvetica", "B", 9)
            self.cell(sidebar_width - 20, 5, "LANGUAGES", 0, 1, 'L')
            self.set_draw(self.accent[0], self.accent[1], self.accent[2])
            self.set_line_width(0.3)
            self.line(10, y_pos + 6, sidebar_width - 10, y_pos + 6)
            
            y_pos += 14
            for lang in languages:
                if y_pos > 250:
                    break
                self.set_xy(12, y_pos)
                self.set_color(self.accent[0], self.accent[1], self.accent[2])
                self.set_font("Helvetica", "", 8)
                self.cell(4, 4, "-", 0, 0, 'L')
                self.set_color(self.text_dark[0], self.text_dark[1], self.text_dark[2])
                self.set_font("Helvetica", "", 7.5)
                self.cell(sidebar_width - 24, 4, lang, 0, 1, 'L')
                y_pos += 5
        
        # CERTIFICATIONS section
        y_pos += 4
        if y_pos < 240 and certifications:
            self.set_xy(10, y_pos)
            self.set_color(self.primary[0], self.primary[1], self.primary[2])
            self.set_font("Helvetica", "B", 9)
            self.cell(sidebar_width - 20, 5, "AWARDS", 0, 1, 'L')
            self.set_draw(self.accent[0], self.accent[1], self.accent[2])
            self.set_line_width(0.3)
            self.line(10, y_pos + 6, sidebar_width - 10, y_pos + 6)
            
            y_pos += 14
            for cert in certifications:
                if y_pos > 250:
                    break
                self.set_xy(12, y_pos)
                self.set_color(self.accent[0], self.accent[1], self.accent[2])
                self.set_font("Helvetica", "", 8)
                self.cell(4, 4, "-", 0, 0, 'L')
                self.set_color(self.text_dark[0], self.text_dark[1], self.text_dark[2])
                self.set_font("Helvetica", "", 7.5)
                wrapped_cert = textwrap.fill(cert, width=18)
                self.multi_cell(sidebar_width - 24, 4, wrapped_cert, 0, 'L')
                y_pos += len(wrapped_cert.split('\n')) * 4 + 2
        
        # Right border line
        self.set_draw(self.primary[0], self.primary[1], self.primary[2])
        self.set_line_width(0.5)
        self.line(sidebar_width, 0, sidebar_width, page_height)
    
    def add_main_content(self, career_objective, personal_mission, experience, education, extra_activities, personal_attributes, references):
        main_x = self.main_x
        main_width = self.main_width
        y_pos = 22
        
        # Name
        self.set_xy(main_x, y_pos)
        self.set_color(self.primary[0], self.primary[1], self.primary[2])
        self.set_font("Helvetica", "B", 22)
        self.cell(main_width, 10, "SHARON AKOTH OTIENO", 0, 1, 'L')
        y_pos += 10
        
        # Title - TWO LINES on main content
        self.set_xy(main_x, y_pos)
        self.set_color(self.accent[0], self.accent[1], self.accent[2])
        self.set_font("Helvetica", "B", 11)
        self.cell(main_width, 6, "Education Professional", 0, 1, 'L')
        y_pos += 6
        
        self.set_xy(main_x, y_pos)
        self.set_color(self.accent[0], self.accent[1], self.accent[2])
        self.set_font("Helvetica", "B", 11)
        self.cell(main_width, 6, "Inclusion Specialist", 0, 1, 'L')
        y_pos += 8
        
        # Decorative line
        self.set_draw(self.accent[0], self.accent[1], self.accent[2])
        self.set_line_width(1)
        self.line(main_x, y_pos, main_x + 60, y_pos)
        y_pos += 10
        
        # CAREER OBJECTIVE
        self.set_xy(main_x, y_pos)
        self.set_color(self.primary[0], self.primary[1], self.primary[2])
        self.set_font("Helvetica", "B", 10)
        self.cell(main_width, 6, "CAREER OBJECTIVE", 0, 1, 'L')
        self.set_draw(self.accent[0], self.accent[1], self.accent[2])
        self.set_line_width(0.3)
        self.line(main_x, y_pos + 7, main_x + 45, y_pos + 7)
        y_pos += 12
        
        self.set_xy(main_x, y_pos)
        self.set_color(self.text_dark[0], self.text_dark[1], self.text_dark[2])
        self.set_font("Helvetica", "", 9)
        wrapped_objective = textwrap.fill(career_objective, width=65)
        self.multi_cell(main_width, 5, wrapped_objective, 0, 'L')
        y_pos += len(wrapped_objective.split('\n')) * 5 + 8
        
        # PERSONAL MISSION
        self.set_xy(main_x, y_pos)
        self.set_color(self.primary[0], self.primary[1], self.primary[2])
        self.set_font("Helvetica", "B", 10)
        self.cell(main_width, 6, "PERSONAL MISSION", 0, 1, 'L')
        self.set_draw(self.accent[0], self.accent[1], self.accent[2])
        self.set_line_width(0.3)
        self.line(main_x, y_pos + 7, main_x + 42, y_pos + 7)
        y_pos += 12
        
        for mission in personal_mission:
            self.set_xy(main_x + 4, y_pos)
            self.set_color(self.accent[0], self.accent[1], self.accent[2])
            self.set_font("Helvetica", "", 9)
            self.cell(4, 5, "-", 0, 0, 'L')
            self.set_color(self.text_dark[0], self.text_dark[1], self.text_dark[2])
            self.set_font("Helvetica", "", 9)
            wrapped_mission = textwrap.fill(mission, width=62)
            self.multi_cell(main_width - 12, 5, wrapped_mission, 0, 'L')
            y_pos += len(wrapped_mission.split('\n')) * 5 + 3
        y_pos += 4
        
        # EXPERIENCE
        self.set_xy(main_x, y_pos)
        self.set_color(self.primary[0], self.primary[1], self.primary[2])
        self.set_font("Helvetica", "B", 10)
        self.cell(main_width, 6, "PROFESSIONAL EXPERIENCE", 0, 1, 'L')
        self.set_draw(self.accent[0], self.accent[1], self.accent[2])
        self.set_line_width(0.3)
        self.line(main_x, y_pos + 7, main_x + 55, y_pos + 7)
        y_pos += 12
        
        for exp in experience:
            if y_pos > 250:
                self.add_new_page_with_sidebar("SHARON AKOTH OTIENO")
                y_pos = 22
                main_x = self.main_x
                main_width = self.main_width
            
            # Company name
            self.set_xy(main_x, y_pos)
            self.set_color(self.primary[0], self.primary[1], self.primary[2])
            self.set_font("Helvetica", "B", 9)
            self.cell(main_width * 0.7, 5, exp["company"], 0, 0, 'L')
            
            self.set_color(self.text_light[0], self.text_light[1], self.text_light[2])
            self.set_font("Helvetica", "I", 8)
            self.cell(main_width * 0.3, 5, exp["date"], 0, 1, 'R')
            y_pos += 5
            
            # Title
            self.set_xy(main_x, y_pos)
            self.set_color(self.accent[0], self.accent[1], self.accent[2])
            self.set_font("Helvetica", "B", 8.5)
            self.cell(main_width, 5, exp["title"], 0, 1, 'L')
            y_pos += 5
            
            # Bullets
            if "bullets" in exp:
                for bullet in exp["bullets"]:
                    if y_pos > 270:
                        self.add_new_page_with_sidebar("SHARON AKOTH OTIENO")
                        y_pos = 22
                        main_x = self.main_x
                        main_width = self.main_width
                    
                    self.set_xy(main_x + 4, y_pos)
                    self.set_color(self.accent[0], self.accent[1], self.accent[2])
                    self.set_font("Helvetica", "", 8)
                    self.cell(4, 4.5, "-", 0, 0, 'L')
                    self.set_color(self.text_dark[0], self.text_dark[1], self.text_dark[2])
                    self.set_font("Helvetica", "", 8.5)
                    wrapped_bullet = textwrap.fill(bullet, width=60)
                    self.multi_cell(main_width - 12, 4.5, wrapped_bullet, 0, 'L')
                    y_pos += len(wrapped_bullet.split('\n')) * 4.5 + 2
            y_pos += 4
        
        # EDUCATION - FIXED SPACING
        y_pos += 4
        if y_pos > 260:
            self.add_new_page_with_sidebar("SHARON AKOTH OTIENO")
            y_pos = 22
            main_x = self.main_x
            main_width = self.main_width
        
        self.set_xy(main_x, y_pos)
        self.set_color(self.primary[0], self.primary[1], self.primary[2])
        self.set_font("Helvetica", "B", 10)
        self.cell(main_width, 6, "EDUCATION", 0, 1, 'L')
        self.set_draw(self.accent[0], self.accent[1], self.accent[2])
        self.set_line_width(0.3)
        self.line(main_x, y_pos + 7, main_x + 35, y_pos + 7)
        y_pos += 12
        
        for edu in education:
            if y_pos > 270:
                self.add_new_page_with_sidebar("SHARON AKOTH OTIENO")
                y_pos = 22
                main_x = self.main_x
                main_width = self.main_width
            
            # School name
            self.set_xy(main_x, y_pos)
            self.set_color(self.primary[0], self.primary[1], self.primary[2])
            self.set_font("Helvetica", "B", 9)
            self.cell(main_width, 5, edu["school"], 0, 1, 'L')
            y_pos += 5
            
            # Degree
            self.set_xy(main_x, y_pos)
            self.set_color(self.text_dark[0], self.text_dark[1], self.text_dark[2])
            self.set_font("Helvetica", "", 8.5)
            
            # Wrap degree text to fit
            degree_text = edu["degree"]
            wrapped_degree = textwrap.fill(degree_text, width=50)
            self.multi_cell(main_width - 10, 4.5, wrapped_degree, 0, 'L')
            y_pos += len(wrapped_degree.split('\n')) * 4.5 + 1
            
            # Date - on a new line
            self.set_xy(main_x + 10, y_pos)
            self.set_color(self.text_light[0], self.text_light[1], self.text_light[2])
            self.set_font("Helvetica", "I", 7.5)
            self.cell(main_width - 20, 4, edu["date"], 0, 1, 'L')
            y_pos += 6
            
            y_pos += 2  # Extra spacing between education entries
        
        # EXTRA-CURRICULAR ACTIVITIES - FIXED WITH BULLETS
        y_pos += 4
        if y_pos > 260:
            self.add_new_page_with_sidebar("SHARON AKOTH OTIENO")
            y_pos = 22
            main_x = self.main_x
            main_width = self.main_width
        
        self.set_xy(main_x, y_pos)
        self.set_color(self.primary[0], self.primary[1], self.primary[2])
        self.set_font("Helvetica", "B", 10)
        self.cell(main_width, 6, "EXTRA-CURRICULAR ACTIVITIES", 0, 1, 'L')
        self.set_draw(self.accent[0], self.accent[1], self.accent[2])
        self.set_line_width(0.3)
        self.line(main_x, y_pos + 7, main_x + 55, y_pos + 7)
        y_pos += 12
        
        # Format activities with bullets
        for activity in extra_activities:
            if y_pos > 270:
                self.add_new_page_with_sidebar("SHARON AKOTH OTIENO")
                y_pos = 22
                main_x = self.main_x
                main_width = self.main_width
            
            self.set_xy(main_x + 4, y_pos)
            self.set_color(self.accent[0], self.accent[1], self.accent[2])
            self.set_font("Helvetica", "", 8)
            self.cell(4, 4, "-", 0, 0, 'L')
            
            self.set_color(self.text_dark[0], self.text_dark[1], self.text_dark[2])
            self.set_font("Helvetica", "", 8.5)
            self.cell(main_width - 16, 4, activity, 0, 1, 'L')
            y_pos += 5
        
        # PERSONAL ATTRIBUTES - FIXED WITH BULLETS
        y_pos += 4
        if y_pos > 260:
            self.add_new_page_with_sidebar("SHARON AKOTH OTIENO")
            y_pos = 22
            main_x = self.main_x
            main_width = self.main_width
        
        self.set_xy(main_x, y_pos)
        self.set_color(self.primary[0], self.primary[1], self.primary[2])
        self.set_font("Helvetica", "B", 10)
        self.cell(main_width, 6, "PERSONAL ATTRIBUTES", 0, 1, 'L')
        self.set_draw(self.accent[0], self.accent[1], self.accent[2])
        self.set_line_width(0.3)
        self.line(main_x, y_pos + 7, main_x + 50, y_pos + 7)
        y_pos += 12
        
        for attr in personal_attributes:
            if y_pos > 270:
                self.add_new_page_with_sidebar("SHARON AKOTH OTIENO")
                y_pos = 22
                main_x = self.main_x
                main_width = self.main_width
            
            self.set_xy(main_x + 4, y_pos)
            self.set_color(self.accent[0], self.accent[1], self.accent[2])
            self.set_font("Helvetica", "", 8)
            self.cell(4, 4.5, "-", 0, 0, 'L')
            self.set_color(self.text_dark[0], self.text_dark[1], self.text_dark[2])
            self.set_font("Helvetica", "", 8.5)
            wrapped_attr = textwrap.fill(attr, width=60)
            self.multi_cell(main_width - 12, 4.5, wrapped_attr, 0, 'L')
            y_pos += len(wrapped_attr.split('\n')) * 4.5 + 3
        
        # REFERENCES
        y_pos += 8
        if y_pos > 260:
            self.add_new_page_with_sidebar("SHARON AKOTH OTIENO")
            y_pos = 22
            main_x = self.main_x
            main_width = self.main_width
        
        self.set_xy(main_x, y_pos)
        self.set_color(self.primary[0], self.primary[1], self.primary[2])
        self.set_font("Helvetica", "B", 10)
        self.cell(main_width, 6, "REFERENCES", 0, 1, 'L')
        self.set_draw(self.accent[0], self.accent[1], self.accent[2])
        self.set_line_width(0.3)
        self.line(main_x, y_pos + 7, main_x + 35, y_pos + 7)
        y_pos += 12
        
        for ref in references:
            if y_pos > 275:
                self.add_new_page_with_sidebar("SHARON AKOTH OTIENO")
                y_pos = 22
                main_x = self.main_x
                main_width = self.main_width
            
            self.set_xy(main_x, y_pos)
            self.set_color(self.primary[0], self.primary[1], self.primary[2])
            self.set_font("Helvetica", "B", 9)
            self.cell(main_width, 5, ref["name"], 0, 1, 'L')
            y_pos += 5
            
            self.set_xy(main_x, y_pos)
            self.set_color(self.text_dark[0], self.text_dark[1], self.text_dark[2])
            self.set_font("Helvetica", "", 8)
            wrapped_title = textwrap.fill(ref["title"], width=55)
            self.multi_cell(main_width, 4, wrapped_title, 0, 'L')
            y_pos += len(wrapped_title.split('\n')) * 4 + 2
            
            self.set_xy(main_x, y_pos)
            self.set_color(self.text_light[0], self.text_light[1], self.text_light[2])
            self.set_font("Helvetica", "", 8)
            self.cell(main_width, 4, ref["address"], 0, 1, 'L')
            y_pos += 4
            
            if ref["phone"]:
                self.set_xy(main_x, y_pos)
                self.set_color(self.text_light[0], self.text_light[1], self.text_light[2])
                self.set_font("Helvetica", "", 8)
                self.cell(main_width, 4, "Phone: " + ref["phone"], 0, 1, 'L')
                y_pos += 4
            
            self.set_xy(main_x, y_pos)
            self.set_color(self.accent[0], self.accent[1], self.accent[2])
            self.set_font("Helvetica", "", 8)
            self.cell(main_width, 4, "Email: " + ref["email"], 0, 1, 'L')
            y_pos += 8
    
    def add_new_page_with_sidebar(self, name):
        """Add a new page with sidebar and main content area"""
        self.add_page()
        
        page_height = 297
        sidebar_width = self.sidebar_width
        
        # Sidebar background
        self.set_fill(self.sidebar_bg[0], self.sidebar_bg[1], self.sidebar_bg[2])
        self.rect(0, 0, sidebar_width, page_height, 'F')
        
        # Decorative top bar
        self.set_fill(self.primary[0], self.primary[1], self.primary[2])
        self.rect(0, 0, 210, 8, 'F')
        
        # Bottom decorative bar
        self.set_fill(self.primary[0], self.primary[1], self.primary[2])
        self.rect(0, page_height - 8, 210, 8, 'F')
        
        # Right border line
        self.set_draw(self.primary[0], self.primary[1], self.primary[2])
        self.set_line_width(0.5)
        self.line(sidebar_width, 0, sidebar_width, page_height)
        
        # Header text on sidebar for new pages
        self.set_xy(8, 25)
        self.set_color(self.primary[0], self.primary[1], self.primary[2])
        self.set_font("Helvetica", "B", 10)
        self.multi_cell(sidebar_width - 16, 5, name.upper(), 0, 'C')
        
        self.set_xy(8, 45)
        self.set_color(self.accent[0], self.accent[1], self.accent[2])
        self.set_font("Helvetica", "B", 7)
        self.cell(sidebar_width - 16, 4, "Education Professional", 0, 1, 'C')
        self.set_xy(8, 49)
        self.set_color(self.accent[0], self.accent[1], self.accent[2])
        self.set_font("Helvetica", "B", 7)
        self.cell(sidebar_width - 16, 4, "Inclusion Specialist", 0, 1, 'C')
        
        self.set_draw(self.accent[0], self.accent[1], self.accent[2])
        self.set_line_width(0.3)
        self.line(18, 53, sidebar_width - 18, 53)
        
        # Page number
        self.set_xy(8, page_height - 20)
        self.set_color(self.text_light[0], self.text_light[1], self.text_light[2])
        self.set_font("Helvetica", "I", 7)
        self.cell(sidebar_width - 16, 4, f"Page {self.page_no()}", 0, 1, 'C')


def create_cv(name, title, contact_info, skills, languages, certifications, 
              career_objective, personal_mission, experience, education, 
              extra_activities, personal_attributes, references, personal_info=None):
    """Create a professional CV for any client"""
    pdf = PDF()
    pdf.add_page()
    
    pdf.add_sidebar(name, title, contact_info, skills, languages, certifications, personal_info)
    pdf.add_main_content(career_objective, personal_mission, experience, education, 
                        extra_activities, personal_attributes, references)
    
    filename = name.upper().replace(" ", "_") + "_CV.pdf"
    pdf.output(filename)
    print(f"✅ CV generated successfully: {filename}")
    return filename


# ============================================
# SHARON AKOTH OTIENO - CV
# ============================================
def create_sharon_cv():
    return create_cv(
        name="Sharon Akoth Otieno",
        title="Education Professional | Inclusion Specialist",
        contact_info={
            "address": "P.O. Box 4703-00100, Nairobi",
            "phone": "+254 703 262 7",
            "email": "sharonotieno4@gmail.com"
        },
        skills=[
            "Classroom Management",
            "Student Support & Mentoring",
            "Inclusion & Special Needs Education",
            "Lesson Planning & Delivery",
            "Behavior Management",
            "Curriculum Development",
            "Student Assessment",
            "Guidance & Counseling",
            "Microsoft Office Suite",
            "Adobe PageMaker"
        ],
        languages=["English (Fluent)", "Kiswahili (Fluent)", "Luo (Fluent)"],
        certifications=[
            "Presidential Awards - Bronze Certificate"
        ],
        career_objective=(
            "To get a challenging job that will enable me to use my knowledge, competencies, "
            "skills and ability. I therefore anticipate working in a highly competitive "
            "environment which prioritize experience conversely achieving and maintaining "
            "professionalism in my designated areas of interest."
        ),
        personal_mission=[
            "My greatest aspiration lies in working in a reputable environment where I will be "
            "able to exploit my professional and personal skills.",
            "Being a strong believer in competition and a team player, I aspire to work in an "
            "establishment whose standards concur with the international benchmark and "
            "consequently this will facilitate me to foster further greater career development."
        ],
        experience=[
            {
                "company": "HILLCREST INTERNATIONAL SCHOOL",
                "title": "Teaching Assistant (Year 1)",
                "date": "January 2024 - Present",
                "bullets": [
                    "Encouraging, supporting and supervising student participation in lessons and other school related activities.",
                    "Supporting teachers to plan learning activities and complete records.",
                    "Helping children who need extra support to complete tasks.",
                    "Helping teachers in managing classroom behavior.",
                    "Getting the classroom ready for lessons."
                ]
            },
            {
                "company": "BRAEBURN KISUMU INTERNATIONAL SCHOOL",
                "title": "FS 1 Volunteer Teacher",
                "date": "January 2022 - March 2022",
                "bullets": [
                    "Encouraging, supporting and supervising student participation in lessons and other school related activities.",
                    "Supporting teachers to plan learning activities and complete records.",
                    "Helping children who need extra support to complete tasks.",
                    "Helping teachers in managing classroom behavior.",
                    "Getting the classroom ready for lessons."
                ]
            },
            {
                "company": "BRAEBURN KISUMU INTERNATIONAL SCHOOL",
                "title": "FS 1 Inclusion Assistant",
                "date": "April 2022 - September 2022",
                "bullets": [
                    "Developing learner's personal organization and social integration.",
                    "Help the learner to work within the boundaries of class rules, maintaining positive behavior.",
                    "Implementing learners specific reward systems to create motivation.",
                    "Ensure adherence to all the school policies and procedures and working closely with the relevant teacher.",
                    "Sharing knowledge of the learner with the parents and those in charge.",
                    "Work with the learners on set targets.",
                    "Being a positive role model especially regarding personal, social and emotional development."
                ]
            },
            {
                "company": "BRAEBURN KISUMU INTERNATIONAL SCHOOL",
                "title": "FS 2 Inclusion Assistant",
                "date": "October 2022 - December 2023",
                "bullets": [
                    "Developing learner's personal organization and social integration.",
                    "Help the learner to work within the boundaries of class rules, maintaining positive behavior.",
                    "Implementing learners specific reward systems to create motivation.",
                    "Ensure adherence to all the school policies and procedures and working closely with the relevant teacher.",
                    "Sharing knowledge of the learner with the parents and those in charge.",
                    "Work with the learners on set targets.",
                    "Being a positive role model especially regarding personal, social and emotional development."
                ]
            },
            {
                "company": "HIGHWAY HIGH SCHOOL, Nairobi",
                "title": "B.O.G Teacher",
                "date": "September 2016 - November 2016",
                "bullets": [
                    "History and Religion teacher.",
                    "Patron of Young Christian Association.",
                    "Badminton club patron.",
                    "Guidance and counseling."
                ]
            },
            {
                "company": "ST. MARY'S MUNDIKA HIGH SCHOOL, Busia",
                "title": "B.O.G Teacher",
                "date": "May 2016 - August 2016",
                "bullets": [
                    "History and Religion teacher.",
                    "Young Christian Association.",
                    "Patron of Badminton club.",
                    "Guidance and Counseling."
                ]
            },
            {
                "company": "ST. ANNE'S KISOKO GIRLS HIGH SCHOOL, Busia",
                "title": "B.O.G Teacher",
                "date": "May 2015 - August 2015",
                "bullets": [
                    "History and Religion teacher.",
                    "Young Christian Association.",
                    "Patron of Badminton club.",
                    "Guidance and Counseling."
                ]
            }
        ],
        education=[
            {
                "school": "Maseno University",
                "degree": "Bachelor of Education Arts with IT (History/Religion) - Second Class (Upper Division)",
                "date": "September 2012 - December 2016"
            },
            {
                "school": "St. Mary's Lwak Girls High School",
                "degree": "Kenya Certificate of Secondary Education (KCSE) - Grade C+ (47 Points)",
                "date": "February 2007 - November 2010"
            },
            {
                "school": "Sinapanga Primary School",
                "degree": "Kenya Certificate of Primary Education (KCPE)",
                "date": "January 1999 - December 2006"
            }
        ],
        extra_activities=[
            "Community Service",
            "Traveling",
            "Networking",
            "Reading business journals, novels and documentaries",
            "Participating in business seminars and forums",
            "Mentoring",
            "Guiding and counseling",
            "Playing badminton"
        ],
        personal_attributes=[
            "Competent, pro-active, self-driven, result oriented and a team player.",
            "Have strong interpersonal skills with ability to work efficiently with minimum supervision."
        ],
        references=[
            {
                "name": "MR. ISAAC YAMO",
                "title": "HEAD OF INCLUSION - Peponi School",
                "address": "P.O. Box 1276-40100, Kisumu",
                "phone": "0722 501 616",
                "email": "Isaac.yamo@braeburn.ac.ke"
            },
            {
                "name": "MS. SURBI VASHISHT",
                "title": "HEAD TEACHER - Hillcrest International School",
                "address": "P.O. Box 24819-0052, Nairobi",
                "phone": "",
                "email": "Surbi.vashisht@hillcrest.ac.ke"
            },
            {
                "name": "MS. EUNICE KAMUNYU",
                "title": "YEAR 1 CLASS TEACHER - Hillcrest International School",
                "address": "P.O. Box 24819-0052, Nairobi",
                "phone": "0724 249 867",
                "email": "Eunice.kamunyu@hillcrest.ac.ke"
            }
        ],
        personal_info={
            "Birth Date": "02 March 1992",
            "Gender": "Female",
            "Nationality": "Kenyan",
            "Religion": "Christian"
        }
    )


if __name__ == "__main__":
    print("🚀 Generating Sharon Akoth Otieno's CV...\n")
    create_sharon_cv()
    print("\n" + "="*50)
    print("✅ CV Generated Successfully!")
    print("📁 File created: SHARON_AKOTH_OTIENO_CV.pdf")
    print("🎨 Professional layout with clean design")
    print("   • No text overlap")
    print("   • Consistent colors")
    print("   • All content from your original CV")
    print("="*50)