from typing import List

def generate_playbook_summary(
    status: str,
    passed_rules: List[str],
    warnings: List[str],
    violations: List[str]
) -> str:
    """
    Generates a natural language summary (Thai/English) of playbook evaluations.
    """
    lines = []
    if status == "PASS":
        lines.append("🛡️ **Playbook Verification: PASS (ผ่านเกณฑ์)**")
        lines.append("ระบบผ่านการตรวจสอบตามกฎวินัยและเงื่อนไข Playbook ครบถ้วน")
    elif status == "WARNING":
        lines.append("⚠️ **Playbook Verification: WARNING (เตือน)**")
        lines.append("มีคำเตือนเกี่ยวกับพฤติกรรมการเทรด:")
        for w in warnings:
            lines.append(f"- {w}")
    else:
        lines.append("🚫 **Playbook Verification: BLOCKED (ระงับการเข้าเทรด)**")
        lines.append("ไม่ผ่านเงื่อนไข Playbook หรือวินัยการควบคุมความเสี่ยง:")
        for v in violations:
            lines.append(f"- 🛑 {v}")
            
    if passed_rules:
        lines.append("\n**กฎที่ผ่านการตรวจสอบสำเร็จ (Passed Rules):**")
        for p in passed_rules[:5]:
            lines.append(f"- ✅ {p}")
        if len(passed_rules) > 5:
            lines.append(f"- ...และกฎอื่น ๆ อีก {len(passed_rules) - 5} กฎ")
            
    return "\n".join(lines)
