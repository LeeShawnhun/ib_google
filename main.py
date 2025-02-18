from fastapi import FastAPI, Request, File, UploadFile, HTTPException, Form
from fastapi.templating import Jinja2Templates
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, HTMLResponse
import shutil
import os
import pandas as pd
from datetime import date
import re
import traceback

# 터미널에 uvicorn main:app --reload 로 실행
app = FastAPI()

# 정적 파일 서빙 설정
app.mount("/static", StaticFiles(directory="static"), name="static")

# 템플릿 설정
templates = Jinja2Templates(directory="templates")

product_idx = {'씨커트': '206', '디커트': '189', '흠집제거제': '16', '유리막코팅제': '15', '연료첨가제': '18', '마카온': '9', '본투식스': '27', '보라샷2.0': '206', '제로픽': '190', '다트너스20.9': '9', 
               '와이블라썸': '199', '와이이뮤': '216', '와이데이': '225', '와이버블': '228', '실프팅앰플': '15', '칼슘아이크림': '16', '리디잇': '12', '리디혈': '13', '리디킬': '18', '리디핏': '14',
               '리디샷': '9', '뉴티엠': '17', '오라컷플러스': '16', '뉴티락': '15', '뉴티캄': '23', '아이치카푸': '23', '아이해피츄': '6', '아이바른풋': '18', '아이튼튼츄': '7', '아이뽀밤부': '13',
               '이지푸': '8', '아이히푸': '14', '아이동그리': '15', '디다샷': '11', '유산균클렌징밀크': '9', '유산균앰플': '10', '닥터33': '192', '닥터33딥샷': '246', '바디미스트': '190', '샤비크': '191',
               '스피큐락셀': '202', '스피카스크럽오일': '222', '바디로션미스트': '224', '닥터란': '24', '닥터모리엔': '9', '투비컷': '84', '2BR': '83', '눈편엔': '76', '판토엔': '210', '아크밀리': '191',
               '라이트유산균포우먼': '10', '톤업엔': '194', '미노샷': '208', '리턴엔': '193', '셀렌톡': '49', '건간엔': '56', '치커트': '51', '크롬컷': '54', '멜라코어3x': '53', '브이젠': '13', '베다이트세럼': '63',
               '반달크림': '17', '핸드문크림': '45','에이트크림': '18', '골드문크림': '19','아이문크림': '24'
               }

def double_check(df_new_merged, new = True):
    today = date.today()
    formatted_date = today.strftime('%y%m%d')
    if new:
        ## 캠페인 네이밍 룰 점검
        df_new_merged["캠페인명 확인"] = False
        # 띄어쓰기 확인
        df_new_merged.loc[df_new_merged['캠페인'].str.contains(" "), '캠페인명 확인'] = True
        # 날짜 확인
        df_new_merged.loc[~df_new_merged['캠페인'].str.contains(formatted_date), '캠페인명 확인'] = True
        # 대문자 확인(2BR은 제외)
        df_new_merged.loc[(df_new_merged['캠페인'].str.replace("2BR", "").str.isupper()), '캠페인명 확인'] = True
        
        ## 광고그룹 네이밍 룰 점검
        df_new_merged["광고그룹명 확인"] = False
        # 띄어쓰기 확인
        df_new_merged.loc[df_new_merged['광고그룹'].str.contains(" "), '광고그룹명 확인'] = True
        # 날짜 확인
        df_new_merged.loc[~df_new_merged['광고그룹'].str.contains(formatted_date), '광고그룹명 확인'] = True
        # 대문자 확인(2BR은 제외)
        df_new_merged.loc[(df_new_merged['광고그룹'].str.replace("2BR", "").str.isupper()), '광고그룹명 확인'] = True

    else:
        df_new_merged["캠페인명 확인"] = False
        df_new_merged["광고그룹명 확인"] = False
    
    ## 광고 네이밍 룰 점검
    df_new_merged["광고명 확인"] = False
    
    # 띄어쓰기 확인
    df_new_merged.loc[df_new_merged['광고 이름'].str.contains(" "), '광고명 확인'] = True

    # 특수문자 & 대문자 확인(2BR은 제외)
    df_new_merged.loc[~(df_new_merged['광고 이름'].str.replace("2BR", "").str.match(r'^[가-힣a-z0-9_]+$')), '광고명 확인'] = True
    
    ## 예산 점검
    df_new_merged["예산 확인"] = True

    # 오늘 날짜가 아닌 것 제외
    df_new_merged.loc[~(df_new_merged['캠페인'].str.contains(formatted_date)), '예산 확인'] = False
    
    # 5만원 or 1만원
    df_new_merged.loc[(df_new_merged['예산'] == 50000) | (df_new_merged['예산'] == 10000), '예산 확인'] = False
    
    ## 최종 url 점검
    df_new_merged["url 확인"] = True
    
    for i in range(len(df_new_merged)):
        name = df_new_merged.loc[i, "제품명"]
        idx = product_idx[name]
        df_new_merged.loc[(df_new_merged["최종 URL"].str.contains(idx)), "url 확인"] = False

    return df_new_merged

def dc_process_files(file_paths):
    txt_file = [x for x in file_paths if x.endswith(".txt")][0]
    csv_files = [x for x in file_paths if x.endswith(".csv")]

    # 텍스트 파일 처리
    with open(txt_file, 'r', encoding='utf-8') as file:
        content = file.read()

    content = content.replace("\n\n", "\n")

    content_split = content.split("====================================")

    new_upload = content_split[0].strip()
    new_campaign = content_split[1].strip()
    new_ads = content_split[2].strip()

    new_upload_list = new_upload.split("-----------------------------------------------------------------")
    new_campaign_list = new_campaign.split("-----------------------------------------------------------------")
    new_ads_list = new_ads.split("-----------------------------------------------------------------")

    # ------------------------------------------------------------------------------------
    # 신규 캠페인 생성
    df_newUpload = pd.DataFrame()
    temp = new_upload_list[0].strip().split("\n")[1:]
    temp_ads = temp[0::2]
    temp_df = pd.DataFrame({
        '광고 이름': temp_ads,
    })
    df_newUpload = pd.concat([df_newUpload, temp_df], axis = 0)

    for campaign in new_upload_list[1:]:
        campaign = campaign.strip().split("\n")
        temp_ads = campaign[0::2]
        temp_df = pd.DataFrame({
            '광고 이름': temp_ads
        })
        
        df_newUpload = pd.concat([df_newUpload, temp_df], axis = 0)

    df_newUpload = df_newUpload.reset_index(drop = True)

    df_newCampaign = pd.DataFrame()
    temp = new_campaign_list[0].strip().split("\n")[1:]
    temp_ads = temp[0::2]
    temp_df = pd.DataFrame({
        '광고 이름': temp_ads,
    })
    df_newCampaign = pd.concat([df_newCampaign, temp_df], axis = 0)

    for campaign in new_campaign_list[1:]:
        campaign = campaign.strip().split("\n")
        temp_ads = campaign[0::2]
        temp_df = pd.DataFrame({
            '광고 이름': temp_ads,
        })
        
        df_newCampaign = pd.concat([df_newCampaign, temp_df], axis = 0)

    df_newCampaign = df_newCampaign.reset_index(drop = True)

    df_new = pd.concat([df_newUpload, df_newCampaign], axis = 0).reset_index(drop=True)
    df_new["제품명"] =df_new["광고 이름"].str.split("_").str[0]

    # ------------------------------------------------------------------------------------
    # 소재 추가
    df_newAds = pd.DataFrame()
    temp = new_ads_list[0].strip().split("\n")[1:]
    temp_ads = temp[1::2]
    temp_df = pd.DataFrame({
        '캠페인': [temp[0]] * len(temp_ads),
        '광고 이름': temp_ads,
    })

    df_newAds = pd.concat([df_newAds, temp_df], axis = 0)

    for campaign in new_ads_list[1:]:
        campaign = campaign.strip().split("\n")
        temp_ads = campaign[1::2]
        temp_df = pd.DataFrame({
            '캠페인': [campaign[0]] * len(temp_ads),
            '광고 이름': temp_ads,
        })

        df_newAds = pd.concat([df_newAds, temp_df], axis = 0)

    df_newAds = df_newAds.reset_index(drop = True)
    df_newAds["제품명"] =df_newAds["광고 이름"].str.split("_").str[0]

    # ------------------------------------------------------------------------------------
    # csv 파일 처리
    df = pd.DataFrame()

    for csv_path in csv_files:
        temp = pd.read_csv(
            csv_path, 
            encoding="UTF-16",
            sep='\t',
            usecols=['캠페인', '광고그룹', '광고 이름', '최종 URL', '예산'],
            header=2)
        
        df = pd.concat([df, temp], axis = 0).reset_index(drop=True)

    df_new_merged = pd.merge(df_new, df, how="inner", on="광고 이름")
    df_existing_merged = pd.merge(df_newAds, df, how="inner", on=["캠페인", "광고 이름"])

    df = double_check(df_new_merged)
    df2 = double_check(df_existing_merged, False)

    df = pd.concat([df, df2], axis = 0).reset_index(drop= True)

    return df

@app.post("/doublecheck/")
async def create_upload_files(request: Request, files: list[UploadFile] = File(...)):
    try:
        # 파일 처리하기
        file_paths = []
        for file in files:
            file_path = os.path.join("temp", file.filename)
            os.makedirs("temp", exist_ok=True)
            with open(file_path, "wb") as buffer:
                shutil.copyfileobj(file.file, buffer)
            file_paths.append(file_path)

        df = dc_process_files(file_paths)
        
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
    
team_brands = {
    "team1": ['비아벨로', '라이브포레스트', '겟비너스', '본투비맨', '마스터벤', '안마디온', '다트너스', '뮤끄', '프렌냥'],
    "team2A": ['해피토리', '뉴티365', '디다', '아비토랩'],
    "team2B": ['씨퓨리', '리베니프', '리디에뜨', '에르보떼'],
    "team3": ['하아르', '리서쳐스', '리프비기닝', '리서쳐스포우먼', '아르다오'],
    "team4": ['베다이트', '데이배리어', '리프비기닝', '건강도감', '리서쳐스포우먼']
}

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
async def create_upload_files(request: Request, files: list[UploadFile] = File(...), selected_team: str = Form(...)):
    try:
        file_paths = []
        for file in files:
            file_path = os.path.join("temp", file.filename)  # 'temp' 디렉토리에 파일 저장
            os.makedirs("temp", exist_ok=True)  # 'temp' 디렉토리가 없으면 생성
            with open(file_path, "wb") as buffer:
                shutil.copyfileobj(file.file, buffer)
            file_paths.append(file_path)
        
        # 선택된 팀의 브랜드 순서 가져오기
        team_brands_list = team_brands.get(selected_team, [])
        
        # 파일 경로를 브랜드 순서에 따라 정렬
        sorted_file_paths = []
        for brand in team_brands_list:
            for file_path in file_paths:
                if f"_{brand}.csv" in file_path:
                    sorted_file_paths.append(file_path)
                    break
        
        # 정렬된 파일 경로로 처리
        processed_file = process_files(sorted_file_paths)
        
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

@app.get("/doublecheck")
async def doublecheck_page(request: Request):
    return templates.TemplateResponse("doublecheck.html", {"request": request})

@app.get("/", response_class=HTMLResponse)
async def read_root(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)