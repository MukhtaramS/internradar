import unittest

from radar import classify


class KindTest(unittest.TestCase):
    def test_kinds(self):
        self.assertEqual(classify.kind("Software Engineering Intern, Summer 2027"), "Internship")
        self.assertEqual(classify.kind("Werkstudent Data Science (m/w/d)"), "Working student")
        self.assertEqual(classify.kind("Master Thesis: LLM Evaluation"), "Thesis")
        self.assertEqual(classify.kind("Industrial Placement – Software"), "Placement")
        self.assertEqual(classify.kind("Quantitative Trader Off-Cycle"), "Internship")

    def test_not_internships(self):
        self.assertIsNone(classify.kind("Internal Tools Engineer"))
        self.assertIsNone(classify.kind("International Tax Manager"))
        self.assertIsNone(classify.kind("Senior Software Engineer"))


class RoleTest(unittest.TestCase):
    def test_roles(self):
        cases = {
            "Software Engineering Intern": "Software",
            "Quantitative Researcher Intern": "Quant Research",
            "Quantitative Trader Intern": "Quant Trading",
            "Trading Systems Software Engineer Intern": "Software",
            "Low-Latency Trading Infrastructure Intern": "Infrastructure",
            "Machine Learning Engineer Intern": "AI/ML",
            "Research Scientist Intern, LLMs (PhD)": "AI/ML",
            "Data Engineering Intern": "Data",
            "Security Engineer Intern": "Security",
            "FPGA Engineer Intern": "Hardware",
            "iOS Engineer Intern": "Mobile",
            "Site Reliability Engineer Intern": "Infrastructure",
            "Software Engineer Intern, Talent Platform": "Software",
            "Circuit Design Intern (m/f/d)": "Hardware",
            "SoC Physical Design Intern (m/f/d)": "Hardware",
            "GPU Internships - RTL Design, RTL Power Optimisation & Physical Design": "Hardware",
            "Formal Verification Intern": "Hardware",
            "Internship - Modem Functional Test - Wireless Technologies & Ecosystems": "Hardware",
            "Microsoft Research Cambridge Internship Program - Machine Intelligence": "AI/ML",
            "Technical Internship - Apple Wallet, Payments & Commerce": "Software",
        }
        for title, want in cases.items():
            self.assertEqual(classify.role(title), want, title)

    def test_out_of_scope(self):
        for title in ["Sales Intern", "Legal Intern", "Marketing Internship",
                      "Operations Intern", "Recruiting Coordinator Intern",
                      "Solutions Engineer Intern", "Data Center Technician Intern",
                      "(Physical) Security Specialist Intern - 2027 Internship",
                      "2027 Pathways Internship – MBA & Master of Engineering | Operations Leadership",
                      "Operations Engineering Intern - start date Q1 2027",
                      "Cloud Support Associate Internship - April 2027 start"]:
            self.assertIsNone(classify.role(title), title)


class DegreeSeasonTest(unittest.TestCase):
    def test_degrees(self):
        self.assertEqual(classify.degrees("Research Scientist Intern (PhD)"), ["PhD"])
        self.assertEqual(classify.degrees("2027 Intern, BS/MS, Software"), ["BS", "MS"])
        self.assertEqual(classify.degrees("Intern, Undergraduate"), ["BS"])
        self.assertEqual(classify.degrees("Intern, Graduate"), ["MS", "PhD"])
        self.assertEqual(classify.degrees("Software Engineering Intern"), [])

    def test_season(self):
        self.assertEqual(classify.season("SWE Intern, Summer 2027"), "Summer 2027")
        self.assertEqual(classify.season("Off-Cycle Quant Intern"), "Off-cycle")
        self.assertEqual(classify.season("2027 Intern - ML"), "2027")
        self.assertIsNone(classify.season("Software Intern"))


if __name__ == "__main__":
    unittest.main()
