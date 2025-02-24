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
from app.doublecheck import *
from app.rejectcheck import *

# 터미널에 uvicorn main:app --reload 로 실행
app = FastAPI()

# 정적 파일 서빙 설정
app.mount("/static", StaticFiles(directory="static"), name="static")

# 템플릿 설정
templates = Jinja2Templates(directory="templates")

@app.post("/doublecheckGoogle/")
async def doublecheckGoogle(request: Request, files: list[UploadFile] = File(...)):
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

@app.post("/doublecheckFacebook/")
async def doublecheckFacebook(request: Request, files: list[UploadFile] = File(...)):
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