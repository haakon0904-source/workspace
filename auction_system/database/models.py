from sqlalchemy import create_engine, Column, Integer, String, Float, DateTime, Text
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from datetime import datetime

Base = declarative_base()

class AuctionProperty(Base):
    __tablename__ = "auction_properties"

    id = Column(Integer, primary_key=True, autoincrement=True)
    case_number = Column(String(50), unique=True)       # 사건번호
    court = Column(String(50))                          # 법원
    region = Column(String(50))                         # 지역
    address = Column(String(200))                       # 주소
    property_type = Column(String(20))                  # 물건종류 (다세대/연립/빌라)
    appraised_value = Column(Float)                     # 감정가
    min_bid_price = Column(Float)                       # 최저입찰가
    auction_date = Column(String(20))                   # 경매기일
    status = Column(String(20))                         # 상태
    area = Column(Float)                                # 전용면적(㎡)
    floor = Column(String(10))                          # 층수
    detail_url = Column(String(500))                    # 상세페이지 URL
    created_at = Column(DateTime, default=datetime.now)
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now)


def get_engine(db_path: str = "auction.db"):
    engine = create_engine(f"sqlite:///{db_path}", echo=False)
    Base.metadata.create_all(engine)
    return engine


def get_session(db_path: str = "auction.db"):
    engine = get_engine(db_path)
    Session = sessionmaker(bind=engine)
    return Session()
