import pandas as pd
from datetime import date

# 구글 더블 체크
def double_check_google(df, product_idx):
    today = date.today()
    formatted_date = today.strftime('%y%m%d')

    ## 캠페인 네이밍 룰 점검
    # 오늘 만들어진 캠페인만 가져오기
    df = df[df['캠페인'].str.contains(formatted_date)].reset_index(drop= True)

    df["캠페인명 확인"] = False

    # 띄어쓰기 확인
    df.loc[df['캠페인'].str.contains(" "), '캠페인명 확인'] = True

    # 대문자 확인(2BR은 제외)
    df.loc[(df['캠페인'].str.replace("2BR", "").str.isupper()), '캠페인명 확인'] = True
    
    # ------------------------------------------------------------------------------------
    ## 광고그룹 네이밍 룰 점검
    df["광고그룹명 확인"] = False

    # 띄어쓰기 확인
    df.loc[df['광고그룹'].str.contains(" "), '광고그룹명 확인'] = True

    # 날짜 확인
    df.loc[~df['광고그룹'].str.contains(formatted_date), '광고그룹명 확인'] = True

    # 대문자 확인(2BR은 제외)
    df.loc[(df['광고그룹'].str.replace("2BR", "").str.isupper()), '광고그룹명 확인'] = True

    # ------------------------------------------------------------------------------------
    ## 광고 네이밍 룰 점검
    df["광고명 확인"] = False
    
    # 띄어쓰기 확인
    df.loc[df['광고 이름'].str.contains(" "), '광고명 확인'] = True

    # 특수문자 & 대문자 확인(2BR은 제외)
    df.loc[~(df['광고 이름'].str.replace("2BR", "").str.match(r'^[가-힣a-z0-9_]+$')), '광고명 확인'] = True
    
    # ------------------------------------------------------------------------------------
    ## 예산 점검
    df["예산 확인"] = True
    
    # 5만원 or 1만원
    df.loc[(df['예산'] == 50000) | (df['예산'] == 10000), '예산 확인'] = False
    
    # ------------------------------------------------------------------------------------
    ## 최종 url 점검
    df["url 확인"] = True
    
    for i in range(len(df)):
        name = df.loc[i, "제품명"]
        idx = str(product_idx[name])

        df.loc[(df["최종 URL"].str.contains(idx)), "url 확인"] = False

    return df

# 구글 파일 전처리
def process_files_doublecheck_google(file_paths):
    campaign_files = [x for x in file_paths if x.endswith("팀.csv")]
    index_file = [x for x in file_paths if x.endswith("구글.csv")][0]

    # 캠페인 csv 파일 처리
    df = pd.DataFrame()

    for csv_path in campaign_files:
        temp = pd.read_csv(
            csv_path, 
            encoding="UTF-16",
            sep='\t',
            usecols=['캠페인', '광고그룹', '광고 이름', '최종 URL', '예산'],
            header=2)
        
        df = pd.concat([df, temp], axis = 0).reset_index(drop=True)

    # index csv 파일 처리
    index_df = pd.read_csv(index_file)
    index_dict = index_df.set_index("제품명")["index"].to_dict()

    df["제품명"] = df["광고그룹"].str.split("_").str[1]
    df = double_check_google(df, index_dict)

    return df

# -------------------------------------------------------------------------
# 페북 더블 체크
def double_check_facebook(df, product_idx):
    today = date.today()
    formatted_date = today.strftime('%y%m%d')

    # 오늘 날짜만 가져오기
    df = df[df["광고 세트 이름"].str.contains(formatted_date)].reset_index(drop= True)

    # abo만 가져오기
    df = df.dropna()
    df = df[~df["캠페인 이름"].str.contains("어드밴티지")].reset_index(drop = True)

    # 예산 정수형으로 바꾸기
    df["광고 세트 예산"] = df["광고 세트 예산"].astype(int)

    # 예산 점검: 5만원
    df["예산 확인"] = True
    df.loc[(df['광고 세트 예산'] == 50000), '예산 확인'] = False

    # 최종 url 점검
    df["제품명"] = df["광고 세트 이름"].str.split("_").str[1]
    df["url 확인"] = True

    for i in range(len(df)):
        name = df.loc[i, "제품명"]
        idx = str(product_idx[name])
        df.loc[(df["웹사이트 URL"].str.contains(idx)), "url 확인"] = False

    return df

# 페북 파일 전처리
def process_files_doublecheck_facebook(file_paths):
    campaign_files = [x for x in file_paths if x.endswith("팀.csv")]
    index_file = [x for x in file_paths if x.endswith("페북.csv")][0]

    # 캠페인 csv 파일 처리
    df = pd.DataFrame()

    for csv_path in campaign_files:
        temp = pd.read_csv(csv_path
                        , usecols = ['캠페인 이름', '광고 세트 이름', '광고 이름', '광고 세트 예산', '광고 세트 예산 유형', '웹사이트 URL'])
        
        df = pd.concat([df, temp], axis = 0).reset_index(drop=True)

    # index csv 파일 처리
    index_df = pd.read_csv(index_file)
    index_dict = index_df.set_index("제품명")["index"].to_dict()

    df = double_check_facebook(df, index_dict)

    return df