from fastapi import FastAPI, Form, Request, File, UploadFile, HTTPException
from fastapi.templating import Jinja2Templates
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, HTMLResponse
import shutil
import os
import pandas as pd
from datetime import date
import re
import traceback
from app.abclal import *

# 터미널에 uvicorn main:app --reload 로 실행
app = FastAPI()

# 정적 파일 서빙 설정
app.mount("/static", StaticFiles(directory="static"), name="static")

# 템플릿 설정
templates = Jinja2Templates(directory="templates")

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

@app.post("/doublecheckGoogle/")
async def create_upload_files_google(request: Request, files: list[UploadFile] = File(...)):
    try:
        # 파일 처리하기
        file_paths = []
        for file in files:
            file_path = os.path.join("temp", file.filename)
            os.makedirs("temp", exist_ok=True)
            with open(file_path, "wb") as buffer:
                shutil.copyfileobj(file.file, buffer)
            file_paths.append(file_path)

        df = process_files_doublecheck_google(file_paths)
        
        for file_path in file_paths:
            os.remove(file_path)

        # 각 조건별 데이터프레임 생성
        df_campaign = df[df["캠페인명 확인"] == True][["캠페인"]].drop_duplicates().reset_index(drop=True)
        df_adgroup = df[df["광고그룹명 확인"] == True][["캠페인", "광고그룹"]].drop_duplicates().reset_index(drop=True)
        df_ad = df[df["광고명 확인"] == True][["캠페인", "광고그룹", "광고 이름"]].reset_index(drop=True)
        df_budget = df[df["예산 확인"] == True][["캠페인"]].drop_duplicates().reset_index(drop=True)
        df_url = df[df["url 확인"] == True][["캠페인", "광고 이름"]].reset_index(drop=True)

        # 기본 컨텍스트 딕셔너리 설정
        context = {
            "request": request,
            "has_campaign": len(df_campaign) > 0,
            "has_adgroup": len(df_adgroup) > 0,
            "has_ad": len(df_ad) > 0,
            "has_budget": len(df_budget) > 0,
            "has_url": len(df_url) > 0
        }

        # 조건부로 HTML 테이블 추가
        if context["has_campaign"]:
            context["campaign_html"] = df_campaign.to_html(classes=['table', 'table-striped'], index=False)
        
        if context["has_adgroup"]:
            context["adgroup_html"] = df_adgroup.to_html(classes=['table', 'table-striped'], index=False)
        
        if context["has_ad"]:
            context["ad_html"] = df_ad.to_html(classes=['table', 'table-striped'], index=False)
        
        if context["has_budget"]:
            context["budget_html"] = df_budget.to_html(classes=['table', 'table-striped'], index=False)
        
        if context["has_url"]:
            context["url_html"] = df_url.to_html(classes=['table', 'table-striped'], index=False)

        return templates.TemplateResponse("doublecheckResult.html", context)
    
    except Exception as e:
        print(f"An error occurred: {str(e)}")
        print(traceback.format_exc())
        raise HTTPException(status_code=500, detail=f"An error occurred: {str(e)}")

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

@app.post("/doublecheckFacebook/")
async def create_upload_files_facebook(request: Request, files: list[UploadFile] = File(...)):
    try:
        # 파일 처리하기
        file_paths = []
        for file in files:
            file_path = os.path.join("temp", file.filename)
            os.makedirs("temp", exist_ok=True)
            with open(file_path, "wb") as buffer:
                shutil.copyfileobj(file.file, buffer)
            file_paths.append(file_path)

        df = process_files_doublecheck_facebook(file_paths)
        
        for file_path in file_paths:
            os.remove(file_path)

        # 각 조건별 데이터프레임 생성
        df_budget = df[df["예산 확인"] == True][["광고 세트 이름"]].drop_duplicates().reset_index(drop=True)
        df_url = df[df["url 확인"] == True][["광고 세트 이름", "광고 이름"]].reset_index(drop=True)

        # 기본 컨텍스트 딕셔너리 설정
        context = {
            "request": request,
            "has_budget": len(df_budget) > 0,
            "has_url": len(df_url) > 0
        }

        # 조건부로 HTML 테이블 추가       
        if context["has_budget"]:
            context["budget_html"] = df_budget.to_html(classes=['table', 'table-striped'], index=False)
        
        if context["has_url"]:
            context["url_html"] = df_url.to_html(classes=['table', 'table-striped'], index=False)

        return templates.TemplateResponse("doublecheckResult.html", context)
    
    except Exception as e:
        print(f"An error occurred: {str(e)}")
        print(traceback.format_exc())
        raise HTTPException(status_code=500, detail=f"An error occurred: {str(e)}")

# -------------------------------------------------------------------------
# 구글 리젝 처리
def reason_preprocessing(text):
    if "클릭베이트" in text:
        return "클릭베이트"
    elif "일부 제한됨" in text:
        return "일부 제한됨"
    elif "신뢰할 수 없는 주장" in text:
        return "신뢰할 수 없는 주장"
    elif '개인 맞춤 광고 정책 내 건강 관련 콘텐츠 (제한됨)' in text:
        return '개인 맞춤 광고 정책 내 건강 관련 콘텐츠'
    else:
        pattern = r"YouTube 광고 요건 - ([^(]+)(?:\([^)]*\))? \(제한됨\)"
        match = re.search(pattern, text)
        if match:
            return match.group(1).strip()
    return text

def process_files(file_paths):
    today = date.today()
    formatted_date = today.strftime("%m%d")
    all_brand_data = []

    for file_path in file_paths:
        temp = pd.read_csv(
            file_path, 
            encoding="UTF-16",
            sep='\t',
            usecols=['광고 이름', '광고 유형', '캠페인', '광고 정책','승인 상태'],
            header=2)
        
        temp = temp[(temp["광고 유형"] == "반응형 동영상 광고") & (temp["승인 상태"] != "승인됨")]
        temp_campaign_name = temp["캠페인"].unique()
        
        for campaign in temp_campaign_name:
            temp_ad_by_campaign = temp[temp["캠페인"] == campaign]
            temp_list = []
            
            for _, row in temp_ad_by_campaign.iterrows():
                name = row['광고 이름']
                reasons = row['광고 정책'].split(";")
                reasons = [x for x in reasons if "(제한 없음)" not in x]
                reasons = [reason_preprocessing(reason) for reason in reasons]
                reasons = ", ".join(reasons)
                temp_list.append(f"{name}({reasons})")
                
            duplicate_check = pd.DataFrame(temp_list)
            reject_ads = duplicate_check[0].unique()
            
            all_brand_data.append(f"{campaign}")
            all_brand_data.extend(reject_ads)
            all_brand_data.append("")

    output_file = f'{formatted_date} 구글 리젝 체크.txt'

    with open(output_file, 'w', encoding='utf-8') as file:
        for line in all_brand_data:
            file.write(f"{line}\n")
    
    return output_file

@app.post("/uploadfiles/")
async def create_upload_files(request: Request, files: list[UploadFile] = File(...)):
    try:
        file_paths = []
        sorted_order = ["겟비너스", "비아벨로", "본투비맨", "라이브포레스트", "하아르", "리서쳐스", "리프비기닝", "리서쳐스포우먼", "아르다오", "데이배리어", "베다이트"]

        for file in files:
            file_path = os.path.join("temp", file.filename)  # 'temp' 디렉토리에 파일 저장
            os.makedirs("temp", exist_ok=True)  # 'temp' 디렉토리가 없으면 생성
            with open(file_path, "wb") as buffer:
                shutil.copyfileobj(file.file, buffer)

            file_paths.append(file_path)

        # 파일 경로를 브랜드 순서에 따라 정렬   
        sorted_file_paths = []
        for brand in sorted_order:
            for file_path in file_paths:
                if f"_{brand}.csv" in file_path:
                    sorted_file_paths.append(file_path)
                    break
        
        if sorted_file_paths:
            for brand in sorted_file_paths:
                file_paths.remove(brand)

            file_paths = sorted_file_paths + file_paths

        # 정렬된 파일 경로로 처리
        processed_file = process_files(file_paths)
        
        # Clean up uploaded files
        for file_path in file_paths:
            os.remove(file_path)
        
        download_link = f'/download/{processed_file}'
        return templates.TemplateResponse("result.html", {"request": request, "download_link": download_link})
    except Exception as e:
        print(f"An error occurred: {str(e)}")
        print(traceback.format_exc())  # 상세한 오류 트레이스백 출력
        raise HTTPException(status_code=500, detail=f"An error occurred: {str(e)}")

@app.get("/download/{filename}")
async def download_file(filename: str):
    if os.path.exists(filename):
        return FileResponse(filename, media_type='text/plain', filename=filename)
    raise HTTPException(status_code=404, detail="File not found")

# -------------------------------------------------------------------------
# 페북 시드 생성
@app.post("/seed")
async def seed_request(
    request: Request,
    access_token: str = Form(...),
    account_id: int = Form(...),
    campaign_id: int = Form(...),
    seed_name: str = Form(...),
    country_code: str = Form(default="KR"),
    ratio: float = Form(default=0.1)
):
    try:
        seed_data = SeedRequest(
            access_token=access_token,
            account_id=account_id,
            campaign_id=campaign_id,
            seed_name=seed_name,
            country_code=country_code,
            ratio=ratio
        )

        status = create_lookalike_audience(
            access_token=seed_data.access_token,
            seed_name=seed_data.seed_name,
            ad_account_id=seed_data.account_id,
            campaign_id=seed_data.campaign_id,
            ratio=seed_data.ratio,
            country=seed_data.country_code
        )

        return templates.TemplateResponse(
            "seedResult.html",
            {
                "request": request,
                "status": status,
                "success": True if "완료" in status else False, 
                "seed_data": seed_data
            }
        )

    except Exception as e:
        error_message = str(e)
        return templates.TemplateResponse(
            "seedResult.html",
            {
                "request": request,
                "status": f"오류 발생: {error_message}",
                "success": False,
                "seed_data": seed_data
            }
        )

@app.get("/doublecheckGoogle", response_class=HTMLResponse)
async def doublecheck_page_google(request: Request):
    return templates.TemplateResponse("doublecheckGoogle.html", {"request": request})

@app.get("/doublecheckFacebook", response_class=HTMLResponse)
async def doublecheck_page_facebook(request: Request):
    return templates.TemplateResponse("doublecheckFacebook.html", {"request": request})

@app.get("/facebookSeedMaker", response_class=HTMLResponse)
async def seedRequest_page(request: Request):
    return templates.TemplateResponse("facebookSeedMaker.html", {"request": request})

@app.get("/", response_class=HTMLResponse)
async def read_root(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)