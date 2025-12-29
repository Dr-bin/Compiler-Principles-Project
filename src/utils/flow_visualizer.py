"""控制流图可视化模块"""
import re
from typing import Optional


class FlowVisualizer:
    """控制流图生成器"""

    def _is_label(self, line: str) -> bool:
        return bool(re.match(r'^L\d+:$', line))

    def _is_conditional_jump(self, line: str) -> bool:
        return line.startswith('if ') and 'goto' in line

    def _is_unconditional_jump(self, line: str) -> bool:
        return line.startswith('goto ')

    def _get_jump_target(self, line: str) -> Optional[str]:
        match = re.search(r'goto\s+(L\d+)', line)
        return match.group(1) if match else None

    def generate_mermaid(self, tac_code: str) -> str:
        """每条指令一个节点"""
        lines_list = [l.strip() for l in tac_code.strip().split('\n') if l.strip()]
        if not lines_list:
            return "graph TD\n    empty[无代码]"
        result = ["graph TD"]
        label_nodes = {}
        jump_edges = []
        for i, line in enumerate(lines_list):
            if self._is_label(line):
                label_nodes[line[:-1]] = f"N{i}"
        for i, line in enumerate(lines_list):
            nid = f"N{i}"
            content = line.replace('"', "'")
            if self._is_label(line):
                result.append(f'    {nid}(["{content}"])')
                if i + 1 < len(lines_list):
                    result.append(f'    {nid} --> N{i+1}')
            elif self._is_conditional_jump(line):
                m = re.match(r'if\s+(.+?)\s+goto\s+(L\d+)', line)
                if m:
                    cond, target = m.groups()
                    result.append(f'    {nid}{{"{cond}?"}}')
                    jump_edges.append((nid, target, "Y"))
                    if i + 1 < len(lines_list):
                        result.append(f'    {nid} -->|N| N{i+1}')
            elif self._is_unconditional_jump(line):
                target = self._get_jump_target(line)
                result.append(f'    {nid}["{content}"]')
                if target:
                    jump_edges.append((nid, target, None))
            else:
                result.append(f'    {nid}["{content}"]')
                if i + 1 < len(lines_list):
                    result.append(f'    {nid} --> N{i+1}')
        for src, target, label in jump_edges:
            if target in label_nodes:
                if label:
                    result.append(f'    {src} -->|{label}| {label_nodes[target]}')
                else:
                    result.append(f'    {src} --> {label_nodes[target]}')
        return "\n".join(result)


    def generate_block_mermaid(self, tac_code: str) -> str:
        """基本块模式：一个基本块一个节点"""
        lines_list = [l.strip() for l in tac_code.strip().split('\n') if l.strip()]
        if not lines_list:
            return "graph TD\n    empty[无代码]"
        leaders = {0}
        for i, line in enumerate(lines_list):
            if self._is_label(line):
                leaders.add(i)
        sorted_leaders = sorted(leaders)
        blocks = []
        for idx, start in enumerate(sorted_leaders):
            end = sorted_leaders[idx + 1] if idx + 1 < len(sorted_leaders) else len(lines_list)
            block_lines = lines_list[start:end]
            lbl = block_lines[0][:-1] if self._is_label(block_lines[0]) else None
            blocks.append({'id': idx, 'lines': block_lines, 'label': lbl})
        label_to_block = {b['label']: b['id'] for b in blocks if b['label']}
        result = ["graph TD"]
        for b in blocks:
            nid = f"B{b['id']}"
            content = "<br/>".join(b['lines']).replace('"', "'")
            last = b['lines'][-1]
            if self._is_conditional_jump(last):
                result.append(f'    {nid}{{"{content}"}}')
            else:
                result.append(f'    {nid}["{content}"]')
        for b in blocks:
            nid = f"B{b['id']}"
            last = b['lines'][-1]
            # 检查块中是否有条件跳转（可能不在最后一行）
            has_cond = any(self._is_conditional_jump(l) for l in b['lines'])
            has_goto = any(self._is_unconditional_jump(l) for l in b['lines'])
            
            if has_cond:
                # 找到条件跳转的目标
                for line in b['lines']:
                    if self._is_conditional_jump(line):
                        target = self._get_jump_target(line)
                        if target and target in label_to_block:
                            result.append(f'    {nid} -->|Y| B{label_to_block[target]}')
                        break
                # 找到无条件跳转的目标（false分支）
                for line in b['lines']:
                    if self._is_unconditional_jump(line):
                        target = self._get_jump_target(line)
                        if target and target in label_to_block:
                            result.append(f'    {nid} -->|N| B{label_to_block[target]}')
                        break
                else:
                    # 没有goto，false分支到下一块
                    if b['id'] + 1 < len(blocks):
                        result.append(f'    {nid} -->|N| B{b["id"] + 1}')
            elif has_goto:
                for line in b['lines']:
                    if self._is_unconditional_jump(line):
                        target = self._get_jump_target(line)
                        if target and target in label_to_block:
                            result.append(f'    {nid} --> B{label_to_block[target]}')
                        break
            else:
                if b['id'] + 1 < len(blocks):
                    result.append(f'    {nid} --> B{b["id"] + 1}')
        return "\n".join(result)


def visualize_tac(tac_code: str, block_mode: bool = False) -> str:
    """将三地址码转换为 Mermaid 控制流图"""
    v = FlowVisualizer()
    return v.generate_block_mermaid(tac_code) if block_mode else v.generate_mermaid(tac_code)
