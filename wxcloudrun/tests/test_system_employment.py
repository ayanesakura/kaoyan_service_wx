from wxcloudrun.score_card.system_employment_score_calculator import SystemEmploymentScoreCalculator
from wxcloudrun.beans.input_models import UserInfo, TargetInfo, SchoolInfo, Area

def test_system_employment_score(school_name: str):
    """测试体制内就业评分卡"""
    try:
        # 创建测试用的用户信息
        user_info = UserInfo(
            signature="测试用户",
            gender="男",
            school="测试大学",
            major="计算机科学与技术",
            grade="大四",
            rank="10%",
            cet="六级",
            hometown=Area(province="北京", city="北京"),
            is_first_time="是"
        )
        
        # 创建测试用的目标信息
        target_info = TargetInfo(
            school_cities=[Area(province="北京", city="北京")],
            majors=["计算机科学与技术"],
            levels=["985"],
            work_cities=[Area(province="北京", city="北京")],
            weights=[],
            directions=[]
        )
        
        # 创建测试用的学校信息
        school_info = SchoolInfo(
            school_name=school_name,
            school_code="10001",
            is_985="1",
            is_211="1",
            departments="计算机学院",
            major="计算机科学与技术",
            major_code="081201",
            blb=[],
            fsx=[],
            directions=[],
            province="北京",
            city="北京"
        )
        
        # 初始化评分计算器
        calculator = SystemEmploymentScoreCalculator(user_info, target_info)
        
        # 计算评分
        score_result = calculator.calculate_total_score(school_info)
        
        # 打印结果
        print(f"\n{school_name}的体制内就业评分结果:")
        print(f"总分: {score_result['total_score']:.2f}")
        print("\n各维度得分:")
        for dimension in score_result['dimension_scores']:
            print(f"\n{dimension['name']}:")
            print(f"  得分: {dimension['score']:.2f}")
            print(f"  权重: {dimension['weight']}")
            print(f"  加权得分: {dimension['weighted_score']:.2f}")
            print(f"  数据来源: {dimension['source']}")
            print(f"  原始值: {dimension.get('raw_value', 'N/A')}")
            print(f"  描述: {dimension['description']}")
            
        return score_result
        
    except Exception as e:
        print(f"测试过程中出错: {str(e)}")
        return None

if __name__ == "__main__":
    # 测试几所不同层级的学校
    schools = [
        "浙江大学"
    ]
    
    for school in schools:
        test_system_employment_score(school)
        print("\n" + "="*50 + "\n") 