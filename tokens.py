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

    # 移除 'colors' 前缀（如果存在）
    if cleaned_parts and cleaned_parts[0] == 'colors':
        cleaned_parts = cleaned_parts[1:]

    # 移除 'base' 前缀（如果存在）
    if cleaned_parts and cleaned_parts[0] == 'base':
        cleaned_parts = cleaned_parts[1:]

    # 移除 'component colors' 前缀（如果存在）
    if cleaned_parts and cleaned_parts[0] == 'component':
        cleaned_parts = cleaned_parts[1:]
    if len(cleaned_parts) > 1 and cleaned_parts[0] == 'colors':
        cleaned_parts = cleaned_parts[1:]

    # 只有节点名是纯数字的时候保留父节点的名称
    if len(cleaned_parts) > 1 and cleaned_parts[-1].isdigit():
        color_name = f"{cleaned_parts[-2]}_{cleaned_parts[-1]}"
        return color_name

    # 否则只使用最后一个节点名
    if len(cleaned_parts) > 1:
        return cleaned_parts[-1]

    return '_'.join(cleaned_parts)


def extract_content_between_spacing_and_bracket(input_string: str) -> str:
    """
    提取字符串中spacing字符前一个点号到最后一个左括号之间的内容
    并将spacing后面的第一个点号替换成下划线，移除其他点号

    例如: "primitives.mode 1.spacing.0 (0px)" -> "spacing_0"
    例如: "primitives.mode 1.spacing.large.value (24px)" -> "spacing_largevalue"

    Args:
        input_string (str): 输入字符串

    Returns:
        str: 提取的内容，如果找不到则返回空字符串
    """
    # 找到最后一个左括号的位置
    last_bracket_pos = input_string.rfind('(')
    if last_bracket_pos == -1:
        return ""

    # 找到spacing字符的位置
    spacing_pos = input_string.find('spacing')
    if spacing_pos == -1:
        return ""

    # 找到spacing前一个点号的位置
    # 从spacing位置向前查找点号
    dot_before_spacing_pos = -1
    for i in range(spacing_pos - 1, -1, -1):
        if input_string[i] == '.':
            dot_before_spacing_pos = i + 1  # 从点号后面一位开始
            break

    if dot_before_spacing_pos == -1:
        return ""

    # 提取内容 (从点号后一位到最后一个左括号前)
    content = input_string[dot_before_spacing_pos:last_bracket_pos].strip()

    # 将spacing后面的第一个点号替换成下划线，移除其他点号
    spacing_index = content.find('spacing')
    if spacing_index != -1:
        # 找到spacing后面的内容
        after_spacing = content[spacing_index + len('spacing'):]
        # 如果spacing后面有内容
        if after_spacing:
            # 找到第一个点号
            first_dot_pos = after_spacing.find('.')
            if first_dot_pos != -1:
                # 将第一个点号替换成下划线，移除其他点号
                before_first_dot = after_spacing[:first_dot_pos]
                after_first_dot = after_spacing[first_dot_pos + 1:].replace('.', '')
                processed_after_spacing = before_first_dot + '_' + after_first_dot
            else:
                # 没有点号，保持原样
                processed_after_spacing = after_spacing

            content = 'spacing' + processed_after_spacing

    return content


def format_spacing_name(name_parts: List[str]) -> str:
    """格式化spacing尺寸名称，采用节点属性+父节点名"""
    if not name_parts:
        return "unknown"

    # 获取最后一个节点名
    last_part = name_parts[-1]

    # 如果节点名有空格，使用空格前的名字
    if ' ' in last_part:
        node_name = last_part.split(' ')[0]
    else:
        node_name = last_part

    # 清理节点名，移除特殊字符
    node_name = re.sub(r'[^a-zA-Z0-9]', '', node_name)

    # 如果有父节点，使用父节点名
    if len(name_parts) > 1:
        parent_part = name_parts[-2]
        # 清理父节点名
        parent_part = re.sub(r'[^a-zA-Z0-9]', '', parent_part)
        return f"{parent_part}_{node_name}"

    return node_name


def is_dimension_node(node: Dict[str, Any]) -> bool:
    """判断是否为尺寸节点"""
    return node.get('type') == 'dimension' and 'value' in node


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

                # 特殊处理 gray 颜色
                if 'gray' in path_str:
                    if 'light mode' in path_str:
                        light_colors[xml_name] = color_value
                    elif 'dark mode' in path_str:
                        dark_colors[xml_name] = color_value
                    else:
                        # 如果没有明确指定模式，同时添加到两个集合
                        light_colors[xml_name] = color_value
                        dark_colors[xml_name] = color_value
                else:
                    # 其他颜色按原来的逻辑处理
                    if should_include_in_light(path_str):
                        light_colors[xml_name] = color_value

                    if should_include_in_dark(path_str):
                        dark_colors[xml_name] = color_value
            else:
                # 继续递归
                traverse_primitive_colors(value, current_path, light_colors, dark_colors)


def traverse_spacing_dimensions(data: Dict[str, Any], path: List[str],
                                dimensions: Dict[str, int]) -> None:
    """遍历primitives模块中的spacing尺寸"""
    for key, value in data.items():
        current_path = path + [key]

        if isinstance(value, dict):
            if is_dimension_node(value):
                # 这是一个尺寸节点
                dimension_value = value['value']
                xml_name = format_spacing_name(current_path)
                dimensions[xml_name] = dimension_value
            else:
                # 继续递归
                traverse_spacing_dimensions(value, current_path, dimensions)


def generate_android_xml(colors: Dict[str, str], output_path: str, file_name: str) -> None:
    """生成Android XML文件"""
    xml_content = '<?xml version="1.0" encoding="utf-8"?>\n'
    xml_content += '<resources>\n'

    # 按名称排序
    for name in sorted(colors.keys()):
        xml_content += f'    <color name="{name}">{colors[name]}</color>\n'

    xml_content += '</resources>'

    # 确保输出目录存在
    os.makedirs(output_path, exist_ok=True)

    # 写入文件
    file_path = os.path.join(output_path, file_name)
    with open(file_path, 'w', encoding='utf-8') as f:
        f.write(xml_content)

    print(f"Generated: {file_path}")


def generate_dimens_xml(dimensions: Dict[str, int], output_path: str, file_name: str) -> None:
    """生成Android dimens.xml文件"""
    xml_content = '<?xml version="1.0" encoding="utf-8"?>\n'
    xml_content += '<resources>\n'

    # 按名称排序
    for name in sorted(dimensions.keys()):
        xml_content += f'    <dimen name="{name}">{dimensions[name]}dp</dimen>\n'

    xml_content += '</resources>'

    # 确保输出目录存在
    os.makedirs(output_path, exist_ok=True)

    # 写入文件
    file_path = os.path.join(output_path, file_name)
    with open(file_path, 'w', encoding='utf-8') as f:
        f.write(xml_content)

    print(f"Generated: {file_path}")


def generate_semantic_dimens_xml(dimensions: Dict[str, int], output_path: str, file_name: str) -> None:
    """生成Android dimens.xml文件"""
    xml_content = '<?xml version="1.0" encoding="utf-8"?>\n'
    xml_content += '<resources>\n'

    # 按名称排序
    for name in sorted(dimensions.keys()):
        xml_content += f'    <dimen name="{name}">@dimen/{dimensions[name]}</dimen>\n'

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


def process_spacing_dimensions(data: Dict[str, Any]) -> Dict[str, int]:
    """处理primitives模块中的spacing尺寸"""
    dimensions = {}

    print("Extracting spacing dimensions...")
    if 'primitives' in data and 'spacing' in data['primitives']:
        traverse_spacing_dimensions(data['primitives']['spacing'], ['spacing'], dimensions)
    else:
        print("Warning: 'spacing' not found in primitives")

    return dimensions


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

    # 以点号分割路径
    path_parts = reference.split('.')

    # 移除 'colors' 和 'base' 前缀
    filtered_parts = []
    for part in path_parts:
        if part not in ['colors', 'base']:
            filtered_parts.append(part)

    # 如果只剩一个部分，直接使用
    if len(filtered_parts) == 1:
        color_name = filtered_parts[0]
    else:
        # 否则使用最后两部分（处理类似 blue_dark_50 的情况）
        color_name = '_'.join(filtered_parts[-2:])

    if color_name and color_name in primitive_color_map:
        return primitive_color_map[color_name]

    print(f"Warning: Could not find color for reference '{reference}' -> '{color_name}'")
    return None


def resolve_color_reference_to_name(reference: str, primitive_color_map: Dict[str, str]) -> str:
    """解析颜色引用，返回primitive color的名称"""
    # 去除开头和结尾的花括号
    if reference.startswith('{') and reference.endswith('}'):
        reference = reference[1:-1]

    # 处理直接的颜色值（以#开头）
    if reference.startswith('#'):
        return None

    # 如果引用以 "primitives." 开头，直接解析
    if reference.startswith('primitives.'):
        return resolve_primitives_reference(reference, primitive_color_map)

    # 如果引用以 "1. color modes" 开头，需要特殊处理
    elif reference.startswith('1. color modes'):
        # 这种情况引用的是semantic color，我们需要找到它最终的primitive引用
        # 但由于我们的设计，这里应该返回None，让semantic color直接引用primitive
        return None

    # 其他情况，尝试解析
    else:
        return resolve_primitives_reference(reference, primitive_color_map)


def resolve_primitives_reference(reference: str, primitive_color_map: Dict[str, str]) -> str:
    """解析primitives引用"""
    # 去掉light mode或dark mode
    reference = re.sub(r'\s*\(light mode\)', '', reference)
    reference = re.sub(r'\s*\(dark mode\)', '', reference)

    # 以点号分割路径
    path_parts = reference.split('.')

    # 移除 'primitives', 'colors', 'base' 等前缀
    filtered_parts = []
    for part in path_parts:
        if part not in ['primitives', 'colors', 'base']:
            # 替换空格为下划线
            part = part.replace(' ', '_')
            if part:
                filtered_parts.append(part)

    # 处理颜色名称
    if len(filtered_parts) >= 2:
        # 最后两部分通常是颜色名和数字（如 brand.600）
        color_name = f"{filtered_parts[-2]}_{filtered_parts[-1]}"

        # 检查是否存在
        if color_name in primitive_color_map:
            return color_name

        # 如果不存在，尝试其他组合
        # 例如：blue dark.600 -> blue_dark_600
        if len(filtered_parts) >= 3:
            color_name = f"{filtered_parts[-3]}_{filtered_parts[-2]}_{filtered_parts[-1]}"
            if color_name in primitive_color_map:
                return color_name

            # 再尝试：blue dark.600 -> blue_dark_600 (去掉空格)
            color_name = f"{filtered_parts[-3]}{filtered_parts[-2]}_{filtered_parts[-1]}"
            if color_name in primitive_color_map:
                return color_name

    # 如果还是找不到，尝试从原始引用中提取
    for part in filtered_parts:
        if part.isdigit() and len(filtered_parts) > 1:
            color_name = f"{filtered_parts[-2]}_{part}"
            if color_name in primitive_color_map:
                return color_name

    print(f"Warning: Could not find color name for reference '{reference}'")
    return None


def get_node_value(json, nodeRef):  #
    paths = nodeRef.split(".")[2:]
    v = json.get('1. color modes')
    for path in paths:
        v = v.get(path)
    return v['value']


def traverse_semantic_colors(full_data: Dict[str, Any], data: Dict[str, Any], path: List[str],
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
                print(f"--{isinstance(reference, str)}")
                if reference.startswith('{1. color modes'):  # 说明引用的是color modes下的节点，找到这个节点读取其value属性。
                    reference = get_node_value(full_data, reference[1:-1])
                primitive_color_name = resolve_color_reference_to_name(reference, primitive_color_map)

                if primitive_color_name:
                    xml_name = format_xml_name(current_path)
                    color_reference = f"@color/{primitive_color_name}"

                    # 根据路径判断是light mode还是dark mode
                    path_str = ' '.join(current_path).lower()

                    if 'light mode' in path_str:
                        light_semantic[xml_name] = color_reference
                    elif 'dark mode' in path_str:
                        dark_semantic[xml_name] = color_reference
                    else:
                        print()
                        # 如果没有明确指定模式，同时添加到两个集合
                        # light_semantic[xml_name] = color_reference
                        # dark_semantic[xml_name] = color_reference
            else:
                # 继续递归
                traverse_semantic_colors(full_data, value, current_path, light_semantic,
                                         dark_semantic, primitive_color_map)


def process_color_modes(data: Dict[str, Any], primitive_color_map: Dict[str, str]) -> Tuple[
    Dict[str, str], Dict[str, str]]:
    """处理color modes节点，提取语义颜色"""
    light_semantic = {}
    dark_semantic = {}

    # 检查可能的color modes键名
    color_modes_key = None
    for key in data.keys():
        if 'color modes' in key.lower():
            color_modes_key = key
            break

    if color_modes_key is None:
        print("Warning: 'color modes' not found in JSON")
        return light_semantic, dark_semantic

    print("Processing semantic colors...")
    traverse_semantic_colors(data, data[color_modes_key], [], light_semantic,
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


def process_semantic_spacing(data: Dict[str, Any]):
    semantic_dimens = {}
    spacing_node = data['3. spacing']
    for k, v in spacing_node.items():
        spacing_name = k
        reference_name = extract_content_between_spacing_and_bracket(v['value'][1:-1])
        semantic_dimens[str.replace(spacing_name, "-", "_")] = reference_name

    return semantic_dimens


def main():
    # JSON文件路径
    json_file = "design-tokens.tokens(1).json"

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

    # 处理spacing尺寸
    dimensions = process_spacing_dimensions(data)
    semantic_dimensions = process_semantic_spacing(data)
    # 处理渐变
    gradients = process_gradients(data)

    # 生成XML文件
    generate_xml_files(light_colors, dark_colors, output_dir)
    generate_semantic_xml_files(light_semantic, dark_semantic, output_dir)
    generate_dimens_xml(dimensions, os.path.join(output_dir, "values"), "dimens.xml")
    generate_semantic_dimens_xml(semantic_dimensions, os.path.join(output_dir, "values"), "semantic_dimens.xml")
    generate_gradient_xml_files(gradients, output_dir)

    # 打印摘要
    print_summary(light_colors, dark_colors, light_semantic, dark_semantic, output_dir)
    print(f"Spacing dimensions: {len(dimensions)}")
    print(f"Gradients: {len(gradients)}")


def is_gradient_node(node: Dict[str, Any]) -> bool:
    """判断是否为渐变节点"""
    return node.get('type') == 'custom-gradient' and 'value' in node


def format_gradient_name(parent_name: str, node_name: str) -> str:
    """格式化渐变名称，按照命名规则处理"""
    # 处理类似 '600 -> 500 (90deg)' 的情况
    if ' -> ' in node_name and '(' in node_name:
        # 提取箭头前后的数字
        parts = node_name.split(' -> ')
        if len(parts) == 2:
            start_num = parts[0].strip()
            end_part = parts[1].split('(')[0].strip()  # 去掉度数部分
            return f"{parent_name}_{start_num}_{end_part}"

    # 其他情况直接拼接
    # 清理名称，移除特殊字符
    parent_clean = re.sub(r'[^a-zA-Z0-9]', '_', parent_name)
    node_clean = re.sub(r'[^a-zA-Z0-9]', '_', node_name)

    # 移除连续的下划线
    parent_clean = re.sub(r'_+', '_', parent_clean).strip('_')
    node_clean = re.sub(r'_+', '_', node_clean).strip('_')

    return f"{parent_clean}_{node_clean}"


def generate_android_gradient_xml(gradient_name: str, rotation: float, start_color: str, end_color: str) -> str:
    """生成单个Android渐变XML内容"""
    # 确保颜色值格式正确
    if not start_color.startswith('#'):
        start_color = f"#{start_color}"
    if not end_color.startswith('#'):
        end_color = f"#{end_color}"

    # 处理8位颜色值（包含透明度）
    if len(start_color) == 9:
        start_color = start_color[:7]  # 去掉透明度
    if len(end_color) == 9:
        end_color = end_color[:7]  # 去掉透明度

    xml_content = f'''<?xml version="1.0" encoding="utf-8"?>
<shape xmlns:android="http://schemas.android.com/apk/res/android"
    android:shape="rectangle">
    <gradient
        android:type="linear"
        android:angle="{int(rotation)}"
        android:startColor="{start_color}"
        android:endColor="{end_color}" />
</shape>'''

    return xml_content


def traverse_gradient_nodes(data: Dict[str, Any], path: List[str], gradients: Dict[str, Dict[str, Any]]) -> None:
    """遍历渐变节点"""
    for key, value in data.items():
        current_path = path + [key]

        if isinstance(value, dict):
            if is_gradient_node(value):
                # 这是一个渐变节点
                gradient_value = value['value']
                rotation = gradient_value.get('rotation', 0)
                stops = gradient_value.get('stops', [])

                # 确保有两个停止点
                if len(stops) >= 2:
                    start_color = stops[0]['color']
                    end_color = stops[1]['color']

                    # 生成XML名称
                    if len(current_path) >= 2:
                        parent_name = current_path[-2]  # 父节点名
                        node_name = current_path[-1]  # 当前节点名
                        xml_name = format_gradient_name(parent_name, node_name)
                    else:
                        xml_name = format_gradient_name('gradient', current_path[-1])

                    gradients[xml_name] = {
                        'rotation': rotation,
                        'start_color': start_color,
                        'end_color': end_color
                    }

                    print(f"Found gradient: {xml_name} - {start_color} -> {end_color} ({rotation}°)")
            else:
                # 继续递归
                traverse_gradient_nodes(value, current_path, gradients)


def process_gradients(data: Dict[str, Any]) -> Dict[str, Dict[str, Any]]:
    """处理gradient模块，提取渐变"""
    gradients = {}

    if 'gradient' not in data:
        print("Warning: 'gradient' module not found in JSON")
        return gradients

    print("Extracting gradients...")
    traverse_gradient_nodes(data['gradient'], [], gradients)

    return gradients


def generate_gradient_xml_files(gradients: Dict[str, Dict[str, Any]], output_dir: str) -> None:
    """生成渐变XML文件"""
    gradient_dir = os.path.join(output_dir, "gradients")
    os.makedirs(gradient_dir, exist_ok=True)

    print(f"Generating gradient XML files in {gradient_dir}...")

    for gradient_name, gradient_data in gradients.items():
        xml_content = generate_android_gradient_xml(
            gradient_name,
            gradient_data['rotation'],
            gradient_data['start_color'],
            gradient_data['end_color']
        )

        file_path = os.path.join(gradient_dir, f"{gradient_name}.xml")
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(xml_content)

        print(f"Generated: {file_path}")


if __name__ == "__main__":
    main()