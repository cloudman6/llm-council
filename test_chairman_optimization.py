#!/usr/bin/env python3
"""
测试优化后的Chairman评估功能
"""

import asyncio
import json
from backend.council import evaluate_convergence

async def test_chairman_evaluation():
    """测试chairman的对比分析功能"""

    # 模拟用户问题
    user_query = "人工智能在医疗诊断中的优势与挑战是什么？"

    # 模拟第一轮的响应（发散阶段）
    round1_responses = [
        {
            "model": "gpt-4",
            "response": """```json
{
  "summary": "AI在医疗诊断中能提高效率，但存在数据质量和算法偏见问题",
  "viewpoints": [
    "AI能够快速分析大量医疗影像和数据",
    "算法偏见可能导致误诊，需要严格验证",
    "数据隐私和安全是主要挑战",
    "医生与AI协作是最佳模式，而非完全替代"
  ],
  "final_answer_candidate": "AI在医疗诊断中主要通过提高效率和准确率发挥作用，但需要解决数据质量、算法偏见和隐私安全等关键挑战。"
}```
            """
        },
        {
            "model": "claude-3-sonnet",
            "response": """```json
{
  "summary": "AI医疗诊断潜力巨大，但技术成熟度和监管框架仍需完善",
  "viewpoints": [
    "AI在早期疾病筛查方面展现出巨大潜力",
    "缺乏统一的评估标准和监管机制",
    "医疗AI的解释性仍然不足",
    "需要建立医生-AI协作的新工作流程"
  ],
  "final_answer_candidate": "AI医疗诊断虽然前景广阔，但在技术成熟度、监管框架和人机协作方面仍面临重大挑战。"
}```
            """
        }
    ]

    # 模拟第一轮的chairman评估
    previous_chairman_assessment = {
        "convergence_score": 0.6,
        "is_converged": False,
        "consensus_points": [
            "AI在医疗诊断中能够提高效率和准确性",
            "存在技术挑战和伦理问题需要解决",
            "医生与AI协作是重要方向"
        ],
        "conflict_points": [
            "AI的成熟度和可靠性评估标准不统一",
            "对于完全替代还是辅助医生存在分歧",
            "监管需求和实施路径的优先级不同"
        ],
        "explanation": "第一轮讨论识别了AI医疗诊断的主要优势和挑战，但在技术成熟度、实施优先级和监管框架方面存在分歧，需要进一步讨论。",
        "questions_for_next_round": [
            "AI医疗诊断在哪些具体疾病领域已经达到临床应用标准？",
            "如何建立有效的AI医疗系统评估和认证机制？",
            "医生-AI协作的最佳实践模式是什么？"
        ],
        "final_integrated_conclusion": ""
    }

    # 模拟第二轮的响应（收敛阶段）
    round2_responses = [
        {
            "model": "gpt-4",
            "response": """```json
{
  "summary": "AI在特定医学影像诊断领域已成熟，但仍需标准化评估",
  "viewpoints": [
    "皮肤癌诊断、糖尿病视网膜病变筛查已有FDA批准产品",
    "需要建立跨医院的AI系统性能基准测试",
    "医生AI协作应采用'AI初筛+医生复核'模式"
  ],
  "conflicts": [
    "对监管严格程度的看法不同"
  ],
  "suggestions": [
    "建议采用分层监管制度",
    "建立公开的AI医疗案例数据库"
  ],
  "final_answer_candidate": ""
}```
            """
        },
        {
            "model": "claude-3-sonnet",
            "response": """```json
{
  "summary": "AI医学影像诊断成熟度最高，但解释性仍需加强",
  "viewpoints": [
    "放射科和病理科AI应用已达到临床实用水平",
    "需要AI系统能够提供决策依据和置信度",
    "应建立持续监测和改进机制"
  ],
  "conflicts": [
    "对AI解释性要求的严格程度"
  ],
  "suggestions": [
    "开发可解释AI技术标准",
    "建立医疗AI伦理审查委员会"
  ],
  "final_answer_candidate": ""
}```
            """
        }
    ]

    print("🧪 测试优化后的Chairman评估功能")
    print("="*60)

    print("\n📋 第一轮Chairman评估:")
    print(f"收敛评分: {previous_chairman_assessment['convergence_score']}/1.0")
    print(f"共识点数量: {len(previous_chairman_assessment['consensus_points'])}")
    print(f"冲突点数量: {len(previous_chairman_assessment['conflict_points'])}")

    print("\n🔄 评估第二轮讨论的收敛状态...")

    # 测试第二轮的chairman评估
    round2_assessment = await evaluate_convergence(
        user_query,
        round2_responses,
        round_number=2,
        previous_chairman_response=previous_chairman_assessment
    )

    print("\n📊 第二轮Chairman评估结果:")
    print("="*40)
    print(f"收敛评分: {round2_assessment.get('convergence_score', 'N/A')}/1.0")
    print(f"是否收敛: {round2_assessment.get('is_converged', 'N/A')}")
    print(f"共识点: {len(round2_assessment.get('consensus_points', []))} 个")
    print(f"冲突点: {len(round2_assessment.get('conflict_points', []))} 个")
    print(f"生成问题: {len(round2_assessment.get('questions_for_next_round', []))} 个")

    if round2_assessment.get('final_integrated_conclusion'):
        print(f"\n🎯 最终结论长度: {len(round2_assessment['final_integrated_conclusion'])} 字符")
        print("结论片段:", round2_assessment['final_integrated_conclusion'][:200] + "...")

    print("\n✅ 测试完成！")

    return round2_assessment

if __name__ == "__main__":
    asyncio.run(test_chairman_evaluation())