from typing import List, Dict, Optional, Any
from pydantic import BaseModel, Field, validator

class Area(BaseModel):
    """地区信息"""
    province: str = Field(..., description="省份")
    city: str = Field(..., description="城市")

    @validator('province', 'city')
    def validate_area(cls, v):
        if not v:
            raise ValueError("省份和城市不能为空")
        return v

    class Config:
        json_schema_extra = {
            "example": {
                "province": "北京",
                "city": "北京"
            }
        }

class UserInfo(BaseModel):
    """用户基本信息"""
    signature: str = Field(default="", description="考生注册的昵称")
    gender: str = Field(default="", description="考生性别")
    school: str = Field(default="", description="考生本（专）科学校")
    major: str = Field(default="", description="考生本（专）科专业")
    grade: str = Field(default="", description="考生当前学级")
    rank: str = Field(default="", description="考生专业排名")
    cet: str = Field(default="", description="考生四六级通过情况")
    hometown: Area = Field(None, description="考生家乡所在城市")
    is_first_time: str = Field(default="", description="考生是否第一次考研")

    class Config:
        json_schema_extra = {
            "example": {
                "signature": "张三",
                "gender": "男",
                "school": "某大学",
                "major": "计算机科学与技术",
                "grade": "大四",
                "rank": "前10%",
                "cet": "六级",
                "hometown": {
                    "province": "北京",
                    "city": "北京"
                },
                "is_first_time": "是"
            }
        }

class Weight(BaseModel):
    """权重信息"""
    name: str = Field(..., description="权重名称")
    val: float = Field(..., description="权重取值")

    @validator('val')
    def validate_val(cls, v):
        if not 0 <= v <= 1:
            raise ValueError('权重值必须在0到1之间')
        return v

class TargetInfo(BaseModel):
    """目标信息"""
    school_cities: List[Area] = Field(default_factory=list, description="考生希望报考学校所在地区")
    majors: List[str] = Field(default_factory=list, description="考生希望报考的专业")
    levels: List[str] = Field(default_factory=list, description="学校层次")
    work_cities: List[Area] = Field(default_factory=list, description="考生的意向工作城市")
    weights: List[Weight] = Field(default_factory=list, description="权重列表")
    directions: List[str] = Field(default_factory=list, description="研究方向")

    @validator('levels')
    def validate_levels(cls, v):
        valid_levels = {'c9', '985', '211', '双一流'}
        for level in v:
            if level.lower() not in valid_levels:
                raise ValueError(f'无效的学校层次: {level}')
        return v

    @validator('work_cities')
    def validate_work_cities(cls, v):
        if len(v) > 3:
            return v[:3]  # 只取前三个城市
        return v

    class Config:
        json_schema_extra = {
            "example": {
                "school_cities": [
                    {"province": "北京", "city": "北京"},
                    {"province": "上海", "city": "上海"}
                ],
                "majors": ["计算机科学与技术", "软件工程"],
                "levels": ["985", "211"],
                "work_cities": [
                    {"province": "广东", "city": "深圳"},
                    {"province": "浙江", "city": "杭州"}
                ],
                "weights": [
                    {"name": "城市", "val": 0.3},
                    {"name": "专业", "val": 0.7}
                ],
                "directions": ["人工智能", "计算机视觉", "机器学习"]
            }
        }

class RequestData(BaseModel):
    """请求数据"""
    user_info: UserInfo
    target_info: TargetInfo

    class Config:
        json_schema_extra = {
            "example": {
                "user_info": UserInfo.Config.json_schema_extra["example"],
                "target_info": TargetInfo.Config.json_schema_extra["example"]
            }
        }

class Subject(BaseModel):
    """考试科目信息"""
    name: str = Field(..., description="科目名称")
    value: str = Field(..., description="科目内容")
    code: str = Field(..., description="科目代码")

class ExamScore(BaseModel):
    """分数信息"""
    subject: str = Field(..., description="科目名称")
    score: float = Field(..., description="分数")

class YearScore(BaseModel):
    """年度分数信息"""
    year: int = Field(..., description="年份")
    data: List[ExamScore] = Field(..., description="分数数据")

class AdmissionRatio(BaseModel):
    """报录比信息"""
    year: int = Field(..., description="年份")
    bk: float = Field(..., description="报考人数")
    lq: float = Field(..., description="录取人数")
    blb: str = Field(..., description="报录比")

class Direction(BaseModel):
    """研究方向信息"""
    ksfs: str = Field(..., description="考试方式")
    xwlx: str = Field(..., description="学位类型")
    yjfxmc: str = Field(..., description="研究方向名称")
    yjfxdm: str = Field(..., description="研究方向代码")
    zsrs: str = Field(..., description="招生人数")
    bz: str = Field(..., description="备注")
    subjects: List[List[Subject]] = Field(..., description="考试科目列表")

class SchoolInfo(BaseModel):
    """学校信息"""
    school_name: str = Field(..., description="学校名称")
    school_code: str = Field(..., description="学校代码")
    is_985: str = Field(..., description="是否985")
    is_211: str = Field(..., description="是否211")
    departments: str = Field(..., description="院系")
    major: str = Field(..., description="专业")
    major_code: str = Field(..., description="专业代码")
    blb: List[Any] = Field(default_factory=list, description="报录比信息")
    fsx: List[Any] = Field(default_factory=list, description="分数线信息")
    directions: List[Any] = Field(default_factory=list, description="研究方向")
    province: str = Field(..., description="省份")
    city: str = Field(..., description="城市")

    class Config:
        json_schema_extra = {
            "example": {
                "school_name": "北京大学",
                "school_code": "10001",
                "is_985": "1",
                "is_211": "1",
                "departments": "哲学系",
                "major": "马克思主义哲学",
                "major_code": "010101",
                "blb": [
                    {
                        "year": 2012,
                        "bk": 22.0,
                        "lq": 2.0,
                        "blb": "9.09%"
                    }
                ],
                "fsx": [
                    {
                        "year": 2018,
                        "data": [
                            {
                                "subject": "政治科一",
                                "score": 50.0
                            }
                        ]
                    }
                ],
                "directions": [
                    {
                        "ksfs": "统考",
                        "xwlx": "学术学位",
                        "yjfxmc": "马克思主义哲学史",
                        "yjfxdm": "01",
                        "zsrs": "专业：2(不含推免)",
                        "bz": "考试科目说明",
                        "subjects": [
                            [
                                {
                                    "name": "政治",
                                    "value": "思想政治理论",
                                    "code": "101"
                                }
                            ]
                        ]
                    }
                ],
                "province": "北京",
                "city": "北京"
            }
        }

class MergeSchoolData(BaseModel):
    """合并后的学校数据"""
    school_name: str = Field(..., description="学校名称")
    education_level: Optional[str] = Field(None, description="办学层次")
    supervisor_dept: Optional[str] = Field(None, description="主管部门")
    province: Optional[str] = Field(None, description="省份")
    city: Optional[str] = Field(None, description="城市")
    overall_satisfaction: Optional[float] = Field(None, description="总体满意度")
    environment_satisfaction: Optional[float] = Field(None, description="环境满意度")
    life_satisfaction: Optional[float] = Field(None, description="生活满意度")
    further_study_rate: Optional[float] = Field(None, description="深造率")
    further_study_number: Optional[float] = Field(None, description="深造人数")
    us_study_ratio: Optional[float] = Field(None, description="美国留学比例")
    abroad_study_ratio: Optional[float] = Field(None, description="出国留学比例")
    rank: Optional[int] = Field(None, description="排名")
    employment_ratio: Optional[float] = Field(None, description="就业率")
    civil_servant_ratio: Optional[float] = Field(None, description="公务员比例")
    institution_ratio: Optional[float] = Field(None, description="事业单位比例")
    state_owned_ratio: Optional[float] = Field(None, description="国企比例")
    english_name: Optional[str] = Field(None, description="英文名")
    school_type: Optional[str] = Field(None, description="学校类型")
    school_tags: Optional[List[str]] = Field(default_factory=list, description="学校标签")

    @validator('school_tags', pre=True)
    def validate_school_tags(cls, v):
        """验证学校标签"""
        if v is None:
            return []
        if isinstance(v, list):
            valid_tags = {'双一流', '985', '211'}
            return [tag for tag in v if tag in valid_tags]
        return []

    @validator('overall_satisfaction', 'environment_satisfaction', 'life_satisfaction')
    def validate_satisfaction(cls, v):
        """验证满意度分数"""
        if v is not None and not (0 <= v <= 5):
            raise ValueError('满意度分数必须在0到5之间')
        return v

    @validator('further_study_rate', 'employment_ratio', 'civil_servant_ratio', 
              'institution_ratio', 'state_owned_ratio', 'us_study_ratio', 'abroad_study_ratio')
    def validate_ratio(cls, v):
        """验证比例数据"""
        if v is not None and not (0 <= v <= 100):
            raise ValueError('比例必须在0到100之间')
        return v

class MergeMajorData(BaseModel):
    """合并后的专业数据"""
    school_name: str = Field(..., description="学校名称")
    major_code: str = Field(..., description="专业代码")
    major_name: str = Field(..., description="专业名称")
    avg_blb_rate: Optional[float] = Field(None, description="平均报录比")
    avg_bk_number: Optional[int] = Field(None, description="平均报考人数")
    avg_lq_number: Optional[int] = Field(None, description="平均录取人数")
    avg_politics_score: Optional[float] = Field(None, description="平均政治分数")
    avg_english_score: Optional[float] = Field(None, description="平均英语分数")
    avg_subject3_score: Optional[float] = Field(None, description="平均专业课1分数")
    avg_subject4_score: Optional[float] = Field(None, description="平均专业课2分数")
    avg_total_score: Optional[float] = Field(None, description="平均总分")
    planned_enrollment: Optional[int] = Field(None, description="计划招生人数")
    major_recommendation: Optional[float] = Field(None, description="专业推荐度")
    overall_satisfaction: Optional[float] = Field(None, description="总体满意度")
    condition_satisfaction: Optional[float] = Field(None, description="条件满意度")
    teaching_satisfaction: Optional[float] = Field(None, description="教学满意度")
    employment_satisfaction: Optional[float] = Field(None, description="就业满意度")
    level: Optional[str] = Field(None, description="学科评估等级")

    @validator('avg_blb_rate')
    def validate_blb_rate(cls, v):
        """验证报录比"""
        if v is not None and v < 0:
            raise ValueError('报录比不能为负数')
        return v

    @validator('avg_bk_number', 'avg_lq_number', 'planned_enrollment')
    def validate_numbers(cls, v):
        """验证人数"""
        if v is not None and v < 0:
            raise ValueError('人数不能为负数')
        return v

    @validator('avg_politics_score', 'avg_english_score')
    def validate_common_scores(cls, v):
        """验证公共课分数"""
        if v is not None and not (0 <= v <= 150):  # 调整为0-150分范围
            raise ValueError('公共课分数必须在0到150之间')
        return v

    @validator('avg_subject3_score', 'avg_subject4_score')
    def validate_subject_scores(cls, v):
        """验证专业课分数"""
        if v is not None and not (0 <= v <= 300):  # 调整为0-300分范围
            raise ValueError('专业课分数必须在0到300之间')
        return v

    @validator('avg_total_score')
    def validate_total_score(cls, v):
        """验证总分"""
        if v is not None and not (0 <= v <= 1000):  # 调整为0-1000分范围
            raise ValueError('总分必须在0到1000之间')
        return v

    @validator('major_recommendation', 'overall_satisfaction', 
              'condition_satisfaction', 'teaching_satisfaction', 
              'employment_satisfaction')
    def validate_satisfaction(cls, v):
        """验证满意度分数"""
        if v is not None and not (0 <= v <= 5):
            raise ValueError('满意度分数必须在0到5之间')
        return v

    @validator('level', pre=True)
    def validate_level(cls, v):
        """验证学科评估等级"""
        if v is not None:
            # 去除前后空格
            v = v.strip()
            valid_levels = {'A+', 'A', 'A-', 'B+', 'B', 'B-', 'C+', 'C', 'C-'}
            if v not in valid_levels:
                raise ValueError(f'无效的学科评估等级: {v}')
        return v
