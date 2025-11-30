#!/usr/bin/env python3
"""
测试优化后的收敛阶段prompt功能
"""

import asyncio
import json
from backend.council import build_convergent_prompt

def test_convergent_prompt_structure():
    """测试收敛阶段prompt的结构和内容"""

    print("🧪 测试优化后的收敛阶段Prompt结构")
    print("="*60)

    # 模拟chairman评估结果
    user_query = "人工智能在医疗诊断中的优势与挑战是什么？"

    consensus_points = [
        "AI在医疗诊断中能够提高效率和准确性",
        "存在技术挑战和伦理问题需要解决",
        "医生与AI协作是重要方向"
    ]

    conflict_points = [
        "AI的成熟度和可靠性评估标准不统一",
        "对于完全替代还是辅助医生存在分歧",
        "监管需求和实施路径的优先级不同"
    ]

    questions = [
        "AI医疗诊断在哪些具体疾病领域已经达到临床应用标准？",
        "如何建立有效的AI医疗系统评估和认证机制？",
        "医生-AI协作的最佳实践模式是什么？"
    ]

    # 构建收敛阶段prompt
    convergent_prompt = build_convergent_prompt(
        user_query=user_query,
        consensus_points=consensus_points,
        conflict_points=conflict_points,
        questions=questions
    )

    print("📋 Prompt基本信息:")
    print(f"总长度: {len(convergent_prompt)} 字符")
    print(f"共识点数量: {len(consensus_points)}")
    print(f"冲突点数量: {len(conflict_points)}")
    print(f"问题数量: {len(questions)}")

    print("\n🔍 Prompt结构分析:")

    # 检查关键组件是否包含
    required_components = [
        "深度分析上一轮讨论结果",
        "共识点深度分析",
        "冲突点深度分析",
        "同意程度",
        "补充说明",
        "立场选择",
        "调和方案",
        "consensus_analysis",
        "conflict_analysis",
        "整合要求"
    ]

    for component in required_components:
        if component in convergent_prompt:
            print(f"✅ 包含: {component}")
        else:
            print(f"❌ 缺失: {component}")

    print("\n📝 Prompt预览（前2000字符）:")
    print("-" * 80)
    print(convergent_prompt[:2000])
    print("..." if len(convergent_prompt) > 2000 else "")
    print("-" * 80)

    print("\n🎯 关键分析要求检查:")

    # 检查共识点分析要求
    consensus_analysis_requirements = [
        "同意程度",
        "补充说明",
        "限制条件",
        "深化理解"
    ]

    print("\n🔹 共识点深度分析要求:")
    for req in consensus_analysis_requirements:
        if req in convergent_prompt:
            print(f"  ✅ {req}")
        else:
            print(f"  ❌ {req}")

    # 检查冲突点分析要求
    conflict_analysis_requirements = [
        "立场选择",
        "调和方案",
        "根本原因",
        "影响评估"
    ]

    print("\n⚡ 冲突点深度分析要求:")
    for req in conflict_analysis_requirements:
        if req in convergent_prompt:
            print(f"  ✅ {req}")
        else:
            print(f"  ❌ {req}")

    return convergent_prompt

def simulate_convergent_response_example():
    """模拟一个优化后的收敛阶段响应示例"""

    print("\n\n🎭 模拟优化后的收敛阶段响应示例")
    print("="*60)

    example_response = {
        "summary": "基于对上一轮共识点和冲突点的深度分析，我认为AI在医疗诊断中的应用主要集中在医学影像领域，但需要建立分层监管机制和医生-AI协作标准。",
        "viewpoints": [
            "AI医疗诊断在特定领域已达到临床应用标准，如皮肤癌筛查和糖尿病视网膜病变",
            "建立分层监管制度是解决AI成熟度和可靠性评估分歧的有效方案",
            "医生-AI协作应采用'AI初筛+医生复核'的标准化流程"
        ],
        "consensus_analysis": [
            {
                "consensus_point": "AI在医疗诊断中能够提高效率和准确性",
                "agreement_level": "完全同意",
                "supplement": "FDA已批准多个AI医疗诊断系统，如IDx-DR用于糖尿病视网膜病变筛查，准确率超过90%",
                "conditions": "主要适用于有明确影像特征的疾病，对复杂罕见病的应用仍有限制",
                "deeper_insight": "AI提高效率主要体现在初筛阶段，诊断复杂病例仍需医生的专业判断"
            },
            {
                "consensus_point": "存在技术挑战和伦理问题需要解决",
                "agreement_level": "部分同意",
                "supplement": "主要挑战是算法偏见、数据隐私和缺乏统一的质量标准",
                "conditions": "伦理问题在不同医疗体系和法律框架下表现不同",
                "deeper_insight": "技术挑战相对容易解决，但伦理和监管挑战需要多方面协作"
            }
        ],
        "conflict_analysis": [
            {
                "conflict_point": "AI的成熟度和可靠性评估标准不统一",
                "your_position": "支持建立分层评估标准，不同应用场景采用不同严格程度",
                "reconciliation_approach": "建立三级认证体系：基础认证（辅助诊断）、高级认证（独立诊断）、专家认证（关键决策）",
                "root_cause": "医疗行业的保守性、缺乏统一的技术标准和法律责任界定不清晰",
                "impact_assessment": "中等影响，通过行业标准组织可以逐步解决"
            }
        ],
        "conflicts": [
            "与其他模型相比，我更强调分层监管而非统一标准",
            "我认为AI应该主要用于辅助而非完全替代，但可以逐步扩大应用范围"
        ],
        "suggestions": [
            "建立国际AI医疗标准组织，制定分层认证体系",
            "开发可解释AI技术，提高医生和患者的信任度",
            "创建AI医疗案例数据库，促进最佳实践分享"
        ],
        "final_answer_candidate": ""
    }

    print("📊 响应结构验证:")

    # 验证所有字段
    expected_fields = [
        "summary", "viewpoints", "consensus_analysis",
        "conflict_analysis", "conflicts", "suggestions", "final_answer_candidate"
    ]

    for field in expected_fields:
        if field in example_response:
            print(f"✅ {field}: {type(example_response[field])}")
        else:
            print(f"❌ 缺失: {field}")

    print("\n🔹 共识点分析示例:")
    if "consensus_analysis" in example_response and example_response["consensus_analysis"]:
        analysis = example_response["consensus_analysis"][0]
        print(f"  共识点: {analysis['consensus_point']}")
        print(f"  同意程度: {analysis['agreement_level']}")
        print(f"  补充说明: {analysis['supplement'][:100]}...")

    print("\n⚡ 冲突点分析示例:")
    if "conflict_analysis" in example_response and example_response["conflict_analysis"]:
        analysis = example_response["conflict_analysis"][0]
        print(f"  冲突点: {analysis['conflict_point']}")
        print(f"  你的立场: {analysis['your_position']}")
        print(f"  调和方案: {analysis['reconciliation_approach'][:100]}...")

    return example_response

def main():
    """主测试函数"""

    print("🚀 收敛阶段Prompt优化测试")
    print("="*80)

    # 测试1: Prompt结构
    convergent_prompt = test_convergent_prompt_structure()

    # 测试2: 模拟响应
    simulate_convergent_response_example()

    print("\n\n📈 优化效果总结")
    print("="*60)
    print("✅ 强化了深度分析要求：共识点和冲突点必须进行多维度分析")
    print("✅ 新增结构化输出：consensus_analysis 和 conflict_analysis 字段")
    print("✅ 明确分析维度：同意程度、补充说明、立场选择、调和方案等")
    print("✅ 强调整合导向：要求将分析与问题回答有机结合")
    print("✅ 提供收敛指导：促进讨论从分歧走向共识的具体路径")

if __name__ == "__main__":
    main()