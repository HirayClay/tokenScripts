#!/usr/bin/env python3
"""
解析设计令牌JSON文件，生成Android平台日夜间模式的颜色XML文件
"""

import json
import os
import re
from typing import Dict, Any, List, Tuple


def load_json_file(file_path: str) -> Dict[str, Any]:
    """加载JSON文件"""
    with open(file_path, 'r', encoding='utf-8') as f:
        return json.load(f)


def is_color_node(node: Dict[str, Any]) -> bool:
    """判断是否为颜色节点"""
    return node.get('type') == 'color' and 'value' in node


def is_light_mode(node_name: str) -> bool:
    """判断是否为日间模式节点"""
    return 'light mode' in node_name.lower()


def should_include_in_light(node_name: str) -> bool:
    """判断是否应该包含在日间模式XML中"""
    return 'light mode' in node_name.lower() or 'light mode' not in node_name.lower()


def should_include_in_dark(node_name: str) -> bool:
    """判断是否应该包含在夜间模式XML中"""
    return 'dark mode' in node_name.lower() or 'light mode' not in node_name.lower()


def extract_color_value(value: str) -> str:
    """提取颜色值，去掉透明度"""
    if len(value) == 9:  # #RRGGBBAA格式
        return value[:7]
    return value


def format_xml_name(name_parts: List[str]) -> str:
    """格式化XML名称，将路径转换为下划线分隔的小写名称"""
    # 清理名称，移除特殊字符和空格
    cleaned_parts = []
    for part in name_parts:
        # 移除 (light mode), (dark mode) 等后缀
        part = re.sub(r'\s*\([^)]*\)', '', part)
        # 替换空格和特殊字符为下划线
        part = re.sub(r'[^a-zA-Z0-9]', '_', part)
        # 移除连续的下划线
        part = re.sub(r'_+', '_', part)
        # 移除开头和结尾的下划线
        part = part.strip('_')
        if part:
            cleaned_parts.append(part.lower())

    return '_'.join(cleaned_parts)


def traverse_primitive_colors(data: Dict[str, Any], path: List[str],
                              light_colors: Dict[str, str],
                              dark_colors: Dict[str, str]) -> None:
    """遍历primitives模块中的颜色"""
    for key, value in data.items():
        current_path = path + [key]

        if isinstance(value, dict):
            if is_color_node(value):
                # 这是一个颜色节点
                color_value = extract_color_value(value['value'])
                xml_name = format_xml_name(current_path)

                # 根据路径判断是否包含light/dark mode
                path_str = ' '.join(current_path).lower()

                if should_include_in_light(path_str):
                    light_colors[xml_name] = color_value

                if should_include_in_dark(path_str):
                    dark_colors[xml_name] = color_value
            else:
                # 继续递归
                traverse_primitive_colors(value, current_path, light_colors, dark_colors)


def generate_android_xml(colors: Dict[str, str], output_path: str, file_name: str) -> None:
    """生成Android XML文件"""
    xml_content = '<?xml version="1.0" encoding="utf-8"?>\n'
    xml_content += '<resources>\n'

    # 按名称排序
    for name in sorted(colors.keys()):
        xml_content += f'    <color name="{name}">#{colors[name]}</color>\n'

    xml_content += '</resources>'

    # 确保输出目录存在
    os.makedirs(output_path, exist_ok=True)

    # 写入文件
    file_path = os.path.join(output_path, file_name)
    with open(file_path, 'w', encoding='utf-8') as f:
        f.write(xml_content)

    print(f"Generated: {file_path}")


def process_primitives(data: Dict[str, Any]) -> Tuple[Dict[str, str], Dict[str, str]]:
    """处理primitives模块，提取颜色"""
    light_colors = {}
    dark_colors = {}

    print("Extracting primitive colors...")
    traverse_primitive_colors(data['primitives'], [], light_colors, dark_colors)

    return light_colors, dark_colors


def generate_xml_files(light_colors: Dict[str, str], dark_colors: Dict[str, str],
                       output_dir: str) -> None:
    """生成Android XML文件"""
    print("Generating Android XML files...")
    generate_android_xml(light_colors, os.path.join(output_dir, "values"), "primitive_color.xml")
    generate_android_xml(dark_colors, os.path.join(output_dir, "values-night"), "primitive_color.xml")


def resolve_color_reference(reference: str, primitive_color_map: Dict[str, str]) -> str:
    """解析颜色引用，从primitive color map中查找对应的颜色值"""
    # 去除开头和结尾的花括号
    if reference.startswith('{') and reference.endswith('}'):
        reference = reference[1:-1]

    # 去掉light mode或dark mode
    reference = re.sub(r'\s*\(light mode\)', '', reference)
    reference = re.sub(r'\s*\(dark mode\)', '', reference)

    # 以点号分割路径，取最后一部分作为颜色名
    path_parts = reference.split('.')
    color_name = path_parts[-1] if path_parts else None

    if color_name and color_name in primitive_color_map:
        return primitive_color_map[color_name]

    print(f"Warning: Could not find color for reference '{reference}'")
    return None


def traverse_semantic_colors(data: Dict[str, Any], path: List[str],
                             light_semantic: Dict[str, str],
                             dark_semantic: Dict[str, str],
                             primitive_color_map: Dict[str, str]) -> None:
    """遍历语义颜色节点"""
    for key, value in data.items():
        current_path = path + [key]

        if isinstance(value, dict):
            if 'value' in value and isinstance(value['value'], str):
                # 这是一个颜色引用节点
                reference = value['value']
                color_value = resolve_color_reference(reference, primitive_color_map)

                if color_value:
                    xml_name = format_xml_name(current_path)

                    # 根据路径判断是light mode还是dark mode
                    path_str = ' '.join(current_path).lower()

                    if 'light mode' in path_str:
                        light_semantic[xml_name] = color_value
                    elif 'dark mode' in path_str:
                        dark_semantic[xml_name] = color_value
                    else:
                        # 如果没有明确指定模式，同时添加到两个集合
                        light_semantic[xml_name] = color_value
                        dark_semantic[xml_name] = color_value
            else:
                # 继续递归
                traverse_semantic_colors(value, current_path, light_semantic,
                                         dark_semantic, primitive_color_map)


def process_color_modes(data: Dict[str, Any], primitive_color_map: Dict[str, str]) -> Tuple[
    Dict[str, str], Dict[str, str]]:
    """处理color modes节点，提取语义颜色"""
    light_semantic = {}
    dark_semantic = {}

    if '1. color modes' not in data:
        print("Warning: 'color modes' not found in JSON")
        return light_semantic, dark_semantic

    print("Processing semantic colors...")
    traverse_semantic_colors(data['1. color modes'], [], light_semantic,
                             dark_semantic, primitive_color_map)

    return light_semantic, dark_semantic


def generate_semantic_xml_files(light_semantic: Dict[str, str],
                                dark_semantic: Dict[str, str],
                                output_dir: str) -> None:
    """生成语义颜色XML文件"""
    print("Generating semantic color XML files...")
    generate_android_xml(light_semantic, os.path.join(output_dir, "values"), "semantic_color.xml")
    generate_android_xml(dark_semantic, os.path.join(output_dir, "values-night"), "semantic_color.xml")


def print_summary(light_colors: Dict[str, str], dark_colors: Dict[str, str],
                  light_semantic: Dict[str, str], dark_semantic: Dict[str, str],
                  output_dir: str) -> None:
    """打印处理结果摘要"""
    print(f"\nSummary:")
    print(f"Light mode primitive colors: {len(light_colors)}")
    print(f"Dark mode primitive colors: {len(dark_colors)}")
    print(f"Light mode semantic colors: {len(light_semantic)}")
    print(f"Dark mode semantic colors: {len(dark_semantic)}")
    print(f"Output directory: {output_dir}")


def main():
    # JSON文件路径
    json_file = "/Users/bjsttlp312/Downloads/design-tokens.tokens(1).json"

    # 输出目录 - 使用当前目录
    output_dir = "."

    # 加载JSON文件
    print("Loading JSON file...")
    try:
        data = load_json_file(json_file)
    except FileNotFoundError:
        print(f"Error: File not found: {json_file}")
        return
    except json.JSONDecodeError as e:
        print(f"Error parsing JSON: {e}")
        return

    # 检查是否有primitives模块
    if 'primitives' not in data:
        print("Error: 'primitives' module not found in JSON")
        return

    # 处理primitives模块
    light_colors, dark_colors = process_primitives(data)

    # 创建primitive color map，合并light和dark模式的所有颜色
    primitive_color_map = {}
    primitive_color_map.update(light_colors)
    primitive_color_map.update(dark_colors)

    # 处理color modes模块（语义颜色）
    light_semantic, dark_semantic = process_color_modes(data, primitive_color_map)

    # 生成XML文件
    generate_xml_files(light_colors, dark_colors, output_dir)
    generate_semantic_xml_files(light_semantic, dark_semantic, output_dir)

    # 打印摘要
    # print_summary(light_colors, dark_colors, light_semantic, dark_semantic, output_dir)


if __name__ == "__main__":
    main()