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
