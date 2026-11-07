"""Read a job title and decide: is it an internship, what kind of role, which degree, which season.

Only tech and quant roles are kept. Sales, legal, HR, marketing, operations and the like
get role=None and are dropped by main.py.
"""
from __future__ import annotations

import re
from typing import List, Optional


def _rx(pattern: str):
    return re.compile(pattern, re.I)


# Kinds of student role, checked in order. "internal" and "international" never match.
KINDS = [
    ("Working student", _rx(r"\bwerkstudent|\bworking student|\bstudent assistant")),
    ("Thesis", _rx(r"\bthesis\b|\babschlussarbeit|\bmasterarbeit|\bbachelorarbeit")),
    ("Placement", _rx(r"\bplacement\b|\bindustrial year|\byear in industry|\bsandwich")),
    ("Internship", _rx(r"\bintern\b|\binterns\b|\binternship|\bco-?op\b|\bpraktikum|\bpraktikant"
                       r"|\bstagiaire|\bstage\b|\boff-?cycle\b|\bsummer analyst|\bsummer associate"
                       r"|\bstudent researcher|\bresearch intern")),
]

# A strong tech signal in the title overrides the exclusions below
# ("Software Engineer Intern, Talent Platform" is still a software role).
STRONG_TECH = _rx(
    r"software|machine learning|deep learning|computer vision|\bml\b|\bai\b|applied scien|"
    r"research scien|data scien|data engineer|quant|full[- ]?stack|front[- ]?end|back[- ]?end|"
    r"\bios\b|android|\bsdet\b|security engineer|cyber|\bnlp\b|\bllm\b|compiler|kernel|fpga|asic|"
    r"\brtl\b|\bsoc\b|circuit|physical design|verification|\bgpu\b|modem|wireless|firmware|"
    r"embedded|machine intelligence|technical intern")

EXCLUDE = _rx(
    r"\bsales\b|account (manag|exec)|business develop|marketing|\bbrand\b|communications|"
    r"recruit|talent|\bhr\b|human resources|people partner|legal|lawyer|counsel|compliance|"
    r"\bfinance\b|accounting|\baudit|tax\b|procurement|supply chain|logistics|facilities|"
    r"real estate|customer (success|support|service)|technician|data cent(er|re)|"
    r"mechanical|civil engineer|manufacturing|construction|operations intern|"
    r"\bdesign(er)?\b(?!.*(verification|engineer))|\bux\b|content|editor|journalis|"
    r"solutions? (engineer|architect)|field engineer|process engineer|retail|store\b|"
    r"physical security|\(physical\)|security specialist|\bmba\b|operations leadership|"
    r"operations engineer(ing)? intern|support associate")

# (role, pattern) checked in order, first match wins. Specific roles come before broad ones.
ROLES = [
    ("Quant Research", _rx(r"quant(itative)? (research|analyst|strateg)|\bquant researcher|"
                           r"\bresearch(er)? .*quant|alpha research|systematic research")),
    ("Quant Trading", _rx(r"\btrader\b|"
                          r"\btrading\b(?!.*(software|developer|engineer|infrastructure|systems|platform|technolog))|"
                          r"quant(itative)? trad|market making")),
    ("Security", _rx(r"security|cyber|infosec|appsec|penetration|red team|cryptograph")),
    ("Hardware", _rx(r"\bfpga\b|\basic\b|hardware|silicon|\bchip\b|\brtl\b|\bsoc\b|"
                     r"verification|physical design|circuit|analog|semiconductor|\bgpu\b|\bvlsi\b|"
                     r"modem|wireless|cellular|\brf\b|antenna")),
    ("AI/ML", _rx(r"\bai\b|artificial intelligence|machine learning|machine intelligence|\bml\b|deep learning|"
                  r"computer vision|\bnlp\b|\bllm|gen ?ai|generative|applied scien|"
                  r"research scien|research engineer|student researcher|robotics|"
                  r"autonom|perception|reinforcement learning|speech|recommend")),
    ("Data", _rx(r"\bdata\b|analytics|business intelligence|\bbi\b")),
    ("Mobile", _rx(r"mobile|\bios\b|android|flutter|react native")),
    ("Frontend", _rx(r"front[- ]?end|web develop|web engineer|\bui engineer|javascript|"
                     r"typescript|\breact\b")),
    ("Infrastructure", _rx(r"back[- ]?end|distributed|infrastructure|platform engineer|cloud|devops|"
                           r"site reliability|\bsre\b|database|storage|network|linux|kernel|"
                           r"embedded|firmware|compiler|operating system|systems engineer|"
                           r"low[- ]latency")),
    ("QA/Test", _rx(r"\bqa\b|quality (assurance|engineer)|test(ing)? engineer|software test|"
                    r"\bsdet\b|validation")),
    ("Software", _rx(r"software|\bswe\b|developer|full[- ]?stack|programmer|engineer|"
                     r"computer science|\bdev\b|\bjava\b|\bpython\b|c\+\+|golang|\brust\b|"
                     r"technology intern|tech intern|technical intern|\bquant\b")),
]

_GRAD = r"(?<!under)\bgrad(uate)?\b|\bpostgrad"
DEGREES = [
    ("BS", _rx(r"\bbachelor|\bb\.?sc?\b|\bb\.s\.|\bb\.?eng\b|\bundergrad")),
    ("MS", _rx(r"\bmaster(?!\s*data)|\bm\.?sc?\b|\bm\.s\.|\bm\.?eng\b|" + _GRAD)),
    ("PhD", _rx(r"\bph\.?\s?d\b|\bdoctor|\bdoktor|" + _GRAD)),
]

SEASON_RE = _rx(r"\b(summer|winter|spring|autumn|fall|off-?cycle)\b")
YEAR_RE = re.compile(r"\b(202[5-9])\b")


def kind(title: str) -> Optional[str]:
    for name, pattern in KINDS:
        if pattern.search(title or ""):
            return name
    return None


def role(title: str) -> Optional[str]:
    t = title or ""
    if not STRONG_TECH.search(t) and EXCLUDE.search(t):
        return None
    for name, pattern in ROLES:
        if pattern.search(t):
            return name
    return None


def degrees(title: str) -> List[str]:
    return [name for name, pattern in DEGREES if pattern.search(title or "")]


def season(title: str) -> Optional[str]:
    """"Summer 2027", "Off-cycle", "2027" or None."""
    s = SEASON_RE.search(title or "")
    y = YEAR_RE.search(title or "")
    word = None
    if s:
        word = s.group(1).lower().replace("offcycle", "off-cycle")
        word = {"fall": "Autumn", "off-cycle": "Off-cycle"}.get(word, word.title())
    if word and y:
        return "{} {}".format(word, y.group(1))
    return word or (y.group(1) if y else None)
