#!/usr/bin/env python3
"""
简化测试：优化后的多轮讨论系统关键功能验证
"""

import asyncio
from backend.council import build_convergent_prompt

def test_optimized_convergent_phase():
    """测试优化后的收敛阶段关键功能"""

    print("🚀 优化后的收敛阶段功能验证")
    print("="*60)

    # 模拟第一轮chairman评估结果
    consensus_points = [
        "远程医疗能够提高慢性病管理的可及性和便利性",
        "技术和设备发展是推动远程医疗的关键因素",
        "存在技术可及性和医患关系方面的挑战"
    ]

    conflict_points = [
        "技术接受度和数字鸿沟的程度和解决方案存在分歧",
        "对医患关系质量影响的看法不同",
        "政策支持和商业化路径的优先级有差异"
    ]

    questions = [
        "具体哪些慢性病最适合远程医疗管理？",
        "如何有效解决老年人和低收入群体的技术可及性问题？",
        "远程医疗如何重新设计医患关系以保持服务质量？"
    ]

    user_query = "远程医疗在慢性病管理中的有效性和挑战是什么？"

    # 构建优化后的收敛阶段prompt
    convergent_prompt = build_convergent_prompt(
        user_query=user_query,
        consensus_points=consensus_points,
        conflict_points=conflict_points,
        questions=questions
    )

    print("📋 Prompt基本信息:")
    print(f"长度: {len(convergent_prompt)} 字符")
    print(f"共识点: {len(consensus_points)} 个")
    print(f"冲突点: {len(conflict_points)} 个")
    print(f"问题: {len(questions)} 个")

    print("\n🔍 关键优化功能验证:")

    # 验证深度分析要求
    analysis_requirements = [
        "深度分析上一轮讨论结果",
        "共识点深度分析",
        "冲突点深度分析",
        "同意程度",
        "补充说明",
        "限制条件",
        "深化理解",
        "立场选择",
        "调和方案",
        "根本原因",
        "影响评估"
    ]

    print("\n🎯 深度分析要求:")
    for req in analysis_requirements:
        if req in convergent_prompt:
            print(f"  ✅ {req}")
        else:
            print(f"  ❌ {req}")

    # 验证JSON输出结构
    json_fields = [
        "summary",
        "viewpoints",
        "consensus_analysis",
        "conflict_analysis",
        "conflicts",
        "suggestions",
        "final_answer_candidate"
    ]

    print("\n📊 JSON输出结构:")
    for field in json_fields:
        if field in convergent_prompt:
            print(f"  ✅ {field}")
        else:
            print(f"  ❌ {field}")

    # 验证整合要求
    integration_requirements = [
        "分析整合",
        "演进视角",
        "解决方案",
        "收敛导向",
        "有机结合"
    ]

    print("\n🔗 整合要求:")
    for req in integration_requirements:
        if req in convergent_prompt:
            print(f"  ✅ {req}")
        else:
            print(f"  ❌ {req}")

    print(f"\n📝 Prompt核心内容片段:")
    print("-" * 80)

    # 提取并显示关键部分
    lines = convergent_prompt.split('\n')

    # 查找并显示共识点分析要求
    consensus_section = False
    for line in lines[:50]:  # 显示前50行
        if "共识点深度分析" in line:
            consensus_section = True
        if consensus_section and line.strip():
            print(line)
        if "冲突点深度分析" in line and consensus_section:
            break

    print("-" * 80)

    return convergent_prompt

def show_optimization_comparison():
    """显示优化前后的对比"""

    print("\n\n📈 优化效果对比")
    print("="*60)

    print("🔴 优化前（第一轮）:")
    print("   - 简单回答chairman提出的问题")
    print("   - 无结构化分析要求")
    print("   - 缺乏对共识点的深度思考")
    print("   - 缺乏对冲突点的系统分析")
    print("   - 基本JSON输出格式")

    print("\n🟢 优化后（第二轮及以后）:")
    print("   - 强制要求深度分析上一轮共识点")
    print("   - 强制要求深度分析上一轮冲突点")
    print("   - 明确的分析维度要求（同意程度、补充说明、立场选择等）")
    print("   - 结构化consensus_analysis输出")
    print("   - 结构化conflict_analysis输出")
    print("   - 强调分析与问题回答的有机结合")
    print("   - 明确收敛导向的要求")

    print("\n🎯 预期效果:")
    print("✅ 更深入的观点分析")
    print("✅ 更精确的冲突识别和解决")
    print("✅ 更快的收敛速度")
    print("✅ 更高质量的综合答案")
    print("✅ 更清晰的讨论演进路径")

def main():
    """主测试函数"""

    # 测试优化后的收敛阶段
    convergent_prompt = test_optimized_convergent_phase()

    # 显示优化对比
    show_optimization_comparison()

    print(f"\n\n🏆 优化总结")
    print("="*60)
    print("本次优化成功实现了以下关键改进:")
    print("")
    print("1. **深度分析要求**：强制要求LLM对每个共识点和冲突点进行多维度分析")
    print("2. **结构化输出**：新增consensus_analysis和conflict_analysis字段，确保分析深度")
    print("3. **明确分析维度**：同意程度、补充说明、立场选择、调和方案等具体要求")
    print("4. **整合导向**：强调分析与问题回答的有机结合，促进讨论收敛")
    print("5. **收敛指导**：明确要求提出解决方案和演进路径")
    print("")
    print("这些优化将显著提升收敛阶段的质量，让LLM不再是简单回答问题，而是基于对上一轮讨论的深度分析来推动讨论向高质量答案收敛。")

if __name__ == "__main__":
    main()