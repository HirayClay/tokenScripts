import json
import xml.etree.ElementTree as ET
from typing import Any
from xml.dom import minidom


def parse_design_tokens(json_file_path):
    # 读取JSON文件
    with open(json_file_path, 'r', encoding='utf-8') as file:
        data = json.load(file)

    return data


def getValue(design_tokens: object, color_item_key: str) -> str:
    key_arrays = color_item_key.split(".")
    m = design_tokens
    for idx, item in enumerate(key_arrays):
        m = m.get(item, {})
    return m.get('value')


def generate_android_colors_xml(design_tokens, output_file_path):
    # 创建XML根元素
    root = ET.Element("resources")

    # 解析primitives中的颜色
    primitives = design_tokens.get('primitives', {})
    colors = primitives.get('colors', {})
    # 遍历所有颜色类别
    for color_category, color_values in colors.items():
        if isinstance(color_values, dict):
            # 处理基础颜色（如base、brand、error等）
            for color_name, color_info in color_values.items():
                if isinstance(color_info, dict) and 'type' in color_info and color_info['type'] == 'color':
                    color_value = color_info.get('value', '')
                    if color_value:
                        # 创建color元素
                        color_element = ET.SubElement(root, "color", name=f"{color_category}_{color_name}")
                        color_element.text = color_value

    # 创建格式化的XML字符串
    rough_string = ET.tostring(root, 'utf-8')
    reparsed = minidom.parseString(rough_string)
    pretty_xml = reparsed.toprettyxml(indent="    ")

    # 写入文件
    with open(output_file_path, 'w', encoding='utf-8') as xml_file:
        xml_file.write(pretty_xml)

    print(f"Android colors XML generated: {output_file_path}")


def generate_android_colors_with_semantic_names(design_tokens, output_file_path):
    # 创建XML根元素
    root = ET.Element("resources")

    # 解析primitives中的颜色
    primitives = design_tokens.get('primitives', {})
    colors = primitives.get('colors', {})

    # 颜色映射到语义名称
    # 生成日间模式颜色
    color_modes = design_tokens.get('1. color modes', {})
    for day_light_mode,modeAttrs in color_modes.items(): #light -dark
        # light_mode_colors = day_light_mode.get('colors', {})
        for k,v in modeAttrs.items(): # colors component-colors
            for color_module_name, color_values in v.items(): #
                # effects部分暂时不处理,不符合颜色json格式,单独处理
                print(f"000-{color_module_name} {color_module_name == 'effects'}")
                if color_module_name == "effects":
                    continue
                # 颜色模块注释
                ET.Comment(f"{color_module_name}")
                for color_sub_name, color_sub_attrs in color_values.items():
                    color_item_name = str.replace(str.split(color_sub_name, " ")[0], "-", "_")
                    color_key_value = color_sub_attrs.get('value')
                    print(f"!!!{color_sub_name} --{color_key_value}")
                    if color_key_value is not None:
                        print(f"!!!{color_item_name}")
                        color_item_key = str.replace(color_key_value, "light mode.", "")
                        color_item_value = getValue(design_tokens, color_item_key[1:-1])
                        color_element = ET.SubElement(root, "color", name=color_item_name)
                        color_element.text = color_item_value
                        # print(f">>>{color_item_name} --{color_key_value}----{color_item_key} --{color_item_value}")
                    else:
                        for color_sub_name2,color_sub_attrs2 in color_sub_attrs.items():
                            color_item_name = str.replace(str.split(color_sub_name2, " ")[0], "-", "_")
                            color_key_value = color_sub_attrs2.get('value')
                            if color_key_value is not None:
                                print(f"!!!{color_item_name}")
                                color_item_key = str.replace(color_key_value, "light mode.", "")
                                color_item_value = getValue(design_tokens, color_item_key[1:-1])
                                color_element = ET.SubElement(root, "color", name=color_item_name)
                                color_element.text = color_item_value
                                # print(f">>>{color_item_name} --{color_key_value}----{color_item_key} --{color_item_value}")


    # 创建格式化的XML字符串
    rough_string = ET.tostring(root, 'utf-8')
    reparsed = minidom.parseString(rough_string)
    pretty_xml = reparsed.toprettyxml(indent="    ")

    # 写入文件
    with open(output_file_path, 'w', encoding='utf-8') as xml_file:
        xml_file.write(pretty_xml)

    print(f"Android colors XML with semantic names generated: {output_file_path}")


def generate_android_gradients(design_tokens, output_file_path):
    # 创建XML根元素
    root = ET.Element("resources")

    # 解析gradients
    gradients = design_tokens.get('gradient', {}).get('gradient', {})

    # 添加注释
    comment = ET.Comment(" Gradient definitions - Note: Android doesn't support gradients in colors.xml natively ")
    root.append(comment)

    for gradient_category, gradient_items in gradients.items():
        if isinstance(gradient_items, dict):
            for gradient_name, gradient_info in gradient_items.items():
                if isinstance(gradient_info, dict) and gradient_info.get('type') == 'custom-gradient':
                    # 创建gradient注释
                    grad_comment = ET.Comment(f" Gradient: {gradient_category}_{gradient_name} ")
                    root.append(grad_comment)

                    # 这里只是示例，实际Android中渐变需要在drawable XML中定义
                    # 我们可以创建一个占位符颜色引用
                    color_element = ET.SubElement(root, "color", name=f"gradient_{gradient_category}_{gradient_name}")
                    color_element.text = "#FF000000"  # 默认黑色

    # 创建格式化的XML字符串
    rough_string = ET.tostring(root, 'utf-8')
    reparsed = minidom.parseString(rough_string)
    pretty_xml = reparsed.toprettyxml(indent="    ")

    # 写入文件
    with open(output_file_path, 'w', encoding='utf-8') as xml_file:
        xml_file.write(pretty_xml)

    print(f"Android gradients XML generated: {output_file_path}")


# 主函数
def main():
    json_file_path = "design-tokens.tokens(1).json"

    # try:
    # 解析设计令牌
    design_tokens = parse_design_tokens(json_file_path)

    # 生成基础颜色XML
    generate_android_colors_xml(design_tokens, "colors_base.xml")

    # 生成带语义名称的颜色XML
    generate_android_colors_with_semantic_names(design_tokens, "colors_semantic.xml")

    # 生成渐变XML（占位符）
    generate_android_gradients(design_tokens, "gradients.xml")

    print("All XML files generated successfully!")

    # except FileNotFoundError:
    #     print(f"Error: File {json_file_path} not found.")
    # except json.JSONDecodeError:
    #     print("Error: Invalid JSON format.")
    # except Exception as e:
    #     print(f"{str(e)}")


if __name__ == "__main__":
    main()
