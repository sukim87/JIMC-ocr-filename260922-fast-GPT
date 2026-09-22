import io
import os
import re
import sys

import easyocr
import numpy as np
import pandas as pd
import pypdfium2 as pdfium
import streamlit as st
from PIL import Image


# ============================================================
# EXE 패키징 시 리소스 경로
# ============================================================
def get_resource_path(relative_path):
    if hasattr(sys, "_MEIPASS"):
        return os.path.join(sys._MEIPASS, relative_path)

    return os.path.join(os.path.abspath("."), relative_path)


# ============================================================
# 메인
# ============================================================
def main():

    # --------------------------------------------------------
    # 웹 페이지 기본 설정
    # --------------------------------------------------------
    st.set_page_config(
        page_title="인수검사서 파일명 자동 생성기 | (주)정우산기",
        page_icon="📄",
        layout="wide",
    )

    # --------------------------------------------------------
    # 사이드바
    # --------------------------------------------------------
    with st.sidebar:

        logo_path = get_resource_path("logo.jpg")

        if not os.path.exists(logo_path):
            logo_path = get_resource_path("세로-영문-Jeongwoo.jpg")

        if os.path.exists(logo_path):
            try:
                st.image(logo_path)
            except Exception:
                pass

        st.markdown("---")

        st.markdown("### 📞 시스템 문의 및 지원")

        st.info(
            """
            **시스템 개발 및 관리자**

            * **부서:** PS품질팀
            * **담당자:** 김선웅
            * **문의 내용:** 프로그램 오류, 수주번호/업체명 추출 규칙 수정 및 변경 요청
            """
        )

        st.markdown("---")

        st.caption(
            "ⓒ Jeongwoo Industrial Machine Co., Ltd. All rights reserved."
        )

    # --------------------------------------------------------
    # 제목
    # --------------------------------------------------------
    UPDATE_DATE = "2026-09-22"

    st.title(
        f"📄 인수검사서 파일명 자동 생성기 `v{UPDATE_DATE}`"
    )

    st.caption(
        f"📅 최종 업데이트: {UPDATE_DATE} | (주)정우산기"
    )

    st.info(
        """
        💡 **사용 안내**

        인수검사 완료한 파일을 스캔 후 첨부하시면 자동으로 제목을 작성하여 드립니다.

        *(기울어지거나 돌아간 스캔 문서도 자동으로 방향을 확인하여 읽습니다.)*

        📌 **파일명 생성 기준**
        `수주번호_날짜_업체명_발주서번호`
        """
    )

    st.markdown("---")

    # ========================================================
    # EasyOCR 모델
    # ========================================================
    @st.cache_resource
    def load_ocr_reader():
        return easyocr.Reader(
            ["ko", "en"],
            gpu=False
        )

    with st.spinner("OCR AI 모델을 로딩 중입니다..."):

        try:
            reader = load_ocr_reader()

        except Exception as e:
            st.error(
                f"OCR AI 모델 로딩 중 오류가 발생했습니다: {e}"
            )
            st.exception(e)
            return

    # ========================================================
    # 수주번호 보정
    # ========================================================
    def clean_and_fix_order_no(order_str):

        if not order_str:
            return ""

        order_upper = order_str.upper().strip()

        # ----------------------------------------------------
        # 수주번호가 될 수 없는 패턴 차단
        # ----------------------------------------------------
        if (
            order_upper.startswith("PO")
            or order_upper.startswith("P0")
            or order_upper.startswith("MI")
        ):
            return ""

        if any(
            bad in order_upper
            for bad in [
                "MATERIAL",
                "MATER1AL",
                "MATL"
            ]
        ):
            return ""

        # ----------------------------------------------------
        # ZNAJOB 패턴
        # ----------------------------------------------------
        if order_upper.startswith("ZNAJOB"):
            return order_str.strip()

        # ----------------------------------------------------
        # M/H/X/P + 2/3/4 형태
        # ----------------------------------------------------
        match = re.search(
            r"([MHXP][234][A-Za-z0-9\-_]+)",
            order_str,
            re.IGNORECASE
        )

        if not match:
            return ""

        raw_order = match.group(1)

        prefix = raw_order[0].upper()
        rest = raw_order[1:]

        parts = re.split(
            r"([\- _])",
            rest
        )

        main_part = parts[0]

        corrected_main = ""

        for idx, char in enumerate(main_part):

            c_upper = char.upper()

            if idx < 6:

                if c_upper in ["O", "Q"]:
                    corrected_main += "0"

                elif c_upper == "Z":
                    corrected_main += "2"

                elif c_upper in ["I", "L"]:
                    corrected_main += "1"

                elif c_upper == "S":
                    corrected_main += "5"

                elif c_upper == "B":
                    corrected_main += "8"

                else:
                    corrected_main += char

            else:
                corrected_main += char

        parts[0] = corrected_main

        return prefix + "".join(parts)

    # ========================================================
    # OCR 이미지 크기 조정
    # ========================================================
    def resize_for_ocr(img, max_width=1800):

        width, height = img.size

        if width <= max_width:
            return img

        ratio = max_width / float(width)

        new_size = (
            int(width * ratio),
            int(height * ratio)
        )

        return img.resize(
            new_size,
            Image.LANCZOS
        )

    # ========================================================
    # 방향 확인용 이미지 크기 조정
    # 방향 판별은 작은 이미지로 빠르게 검사
    # ========================================================
    def resize_for_orientation(img, max_width=900):

        width, height = img.size

        if width <= max_width:
            return img

        ratio = max_width / float(width)

        new_size = (
            int(width * ratio),
            int(height * ratio)
        )

        return img.resize(
            new_size,
            Image.LANCZOS
        )

    # ========================================================
    # 정상 방향인지 빠르게 판단
    # ========================================================
    def is_normal_document(text):

        if not text:
            return False

        text_upper = text.upper()

        keywords = [
            "인수검사",
            "의뢰서",
            "보고서",
            "수주번호",
            "발주서",
            "INSPECTION",
            "RECEIVING",
            "NOTIFICATION",
            "REPORT",
            "ORDER",
            "VENDOR",
            "CUSTOMER",
            "품질",
            "구매",
        ]

        keyword_count = 0

        for kw in keywords:

            if kw.upper() in text_upper:
                keyword_count += 1

        # 수주번호 패턴
        order_match = re.search(
            r"([MHXP][234][A-Z0-9]+|ZNAJOB)",
            text,
            re.IGNORECASE
        )

        if order_match:
            return True

        # 핵심 키워드가 1개 이상 있으면 정상으로 판단
        if keyword_count >= 1:
            return True

        return False

    # ========================================================
    # 빠른 방향 탐지
    #
    # 기존:
    # 0 / 90 / 180 / 270 전부 정밀 OCR
    #
    # 개선:
    # 1. 0도 먼저 OCR
    # 2. 정상으로 보이면 바로 종료
    # 3. 이상하면 작은 이미지로 90/180/270 검사
    # 4. 최종 OCR은 정상 방향에서 한 번만 수행
    # ========================================================
    def detect_orientation_fast(img, ocr_reader):

        orientation_img = resize_for_orientation(
            img,
            max_width=900
        )

        keywords = [
            "인수검사",
            "의뢰서",
            "보고서",
            "수주번호",
            "발주서",
            "INSPECTION",
            "RECEIVING",
            "NOTIFICATION",
            "REPORT",
            "ORDER",
            "VENDOR",
            "CUSTOMER",
            "품질",
            "구매",
        ]

        def quick_score(results):

            extracted_text = " ".join(
                [
                    str(t[1]).strip()
                    for t in results
                    if str(t[1]).strip()
                ]
            )

            score = 0

            text_upper = extracted_text.upper()

            for kw in keywords:

                if kw.upper() in text_upper:
                    score += 15

            if re.search(
                r"([MHXP][234][A-Z0-9]+|ZNAJOB)",
                extracted_text,
                re.IGNORECASE
            ):
                score += 40

            # 텍스트가 어느 정도 있으면 추가 점수
            score += min(
                len(extracted_text),
                30
            )

            return score, extracted_text

        # ----------------------------------------------------
        # 1단계: 0도 검사
        # ----------------------------------------------------
        img_np = np.array(
            orientation_img.convert("RGB")
        )

        try:

            results_0 = ocr_reader.readtext(
                img_np
            )

            score_0, text_0 = quick_score(
                results_0
            )

            if is_normal_document(text_0):

                return 0

        except Exception:
            score_0 = 0

        # ----------------------------------------------------
        # 2단계: 90 / 180 / 270도 검사
        # ----------------------------------------------------
        best_angle = 0
        best_score = score_0

        for angle in [90, 180, 270]:

            try:

                test_img = orientation_img.rotate(
                    angle,
                    expand=True
                )

                test_np = np.array(
                    test_img.convert("RGB")
                )

                results = ocr_reader.readtext(
                    test_np
                )

                score, _ = quick_score(
                    results
                )

                if score > best_score:

                    best_score = score
                    best_angle = angle

            except Exception:
                continue

        return best_angle

    # ========================================================
    # 최종 OCR
    # ========================================================
    def process_ocr_fast(img, ocr_reader):

        # ----------------------------------------------------
        # OCR용 이미지 크기 조정
        # ----------------------------------------------------
        ocr_img = resize_for_ocr(
            img,
            max_width=1800
        )

        # ----------------------------------------------------
        # 방향 확인
        # ----------------------------------------------------
        angle = detect_orientation_fast(
            ocr_img,
            ocr_reader
        )

        # ----------------------------------------------------
        # 최종 방향으로 회전
        # ----------------------------------------------------
        if angle != 0:

            final_img = ocr_img.rotate(
                angle,
                expand=True
            )

        else:
            final_img = ocr_img

        # ----------------------------------------------------
        # 최종 OCR은 한 번만
        # ----------------------------------------------------
        final_np = np.array(
            final_img.convert("RGB")
        )

        results = ocr_reader.readtext(
            final_np
        )

        return results, final_img

    # ========================================================
    # 파일 업로드
    # ========================================================
    uploaded_files = st.file_uploader(
        "PDF 또는 이미지 파일을 선택하세요 (최대 5개)",
        type=[
            "pdf",
            "png",
            "jpg",
            "jpeg"
        ],
        accept_multiple_files=True,
    )

    if uploaded_files:

        st.warning(
            """
            ☕ **잠시 커피 한 잔의 여유를 가져보세요!**

            AI가 문서의 방향을 확인하고 분석합니다.
            이전보다 불필요한 OCR 횟수를 줄여 처리 속도를 개선했습니다. 😊
            """
        )

        # ----------------------------------------------------
        # 최대 5개
        # ----------------------------------------------------
        if len(uploaded_files) > 5:

            st.info(
                "⚠️ 최대 5개까지 한 번에 처리 가능합니다. "
                "상위 5개 파일만 분석합니다."
            )

            target_files = uploaded_files[:5]

        else:

            target_files = uploaded_files

        # ----------------------------------------------------
        # 결과 저장
        # ZIP 사용 안 함
        # ----------------------------------------------------
        processed_results = []

        progress_bar = st.progress(0.0)

        # ====================================================
        # 파일별 처리
        # ====================================================
        for idx, file in enumerate(target_files):

            # ------------------------------------------------
            # 버퍼 위치 초기화
            # ------------------------------------------------
            file.seek(0)

            file_bytes = file.read()

            if not file_bytes:
                continue

            # ------------------------------------------------
            # 확장자
            # ------------------------------------------------
            file_ext = (
                file.name.split(".")[-1].lower()
                if "." in file.name
                else "pdf"
            )

            try:

                image = None

                # ==================================================
                # PDF
                # ==================================================
                if file_ext == "pdf":

                    pdf = pdfium.PdfDocument(
                        file_bytes
                    )

                    page = pdf[0]

                    # 기존 1.8 → 1.4
                    # OCR 속도 개선
                    image = page.render(
                        scale=1.4
                    ).to_pil()

                    pdf.close()

                # ==================================================
                # 이미지
                # ==================================================
                else:

                    image = Image.open(
                        io.BytesIO(file_bytes)
                    )

                # ------------------------------------------------
                # 초기값
                # ------------------------------------------------
                full_text = ""

                df = pd.DataFrame()

                # ==================================================
                # OCR
                # ==================================================
                if image:

                    ocr_results, _ = process_ocr_fast(
                        image,
                        reader
                    )

                    parsed_data = []

                    full_text_list = []

                    # ------------------------------------------------
                    # OCR 결과 정리
                    # ------------------------------------------------
                    for bbox, text, prob in ocr_results:

                        text_clean = str(
                            text
                        ).strip()

                        if not text_clean:
                            continue

                        full_text_list.append(
                            text_clean
                        )

                        top_y = bbox[0][1]

                        left_x = bbox[0][0]

                        parsed_data.append(
                            {
                                "text": text_clean,
                                "top": top_y,
                                "left": left_x,
                                "prob": prob,
                            }
                        )

                    full_text = " ".join(
                        full_text_list
                    )

                    if parsed_data:

                        df = pd.DataFrame(
                            parsed_data
                        )

                    else:

                        df = pd.DataFrame()

                # ==================================================
                # 1. 수주번호 추출
                # ==================================================
                order_no = ""

                order_blacklist = [
                    "ORDER",
                    "URDER",
                    "NUMBER",
                    "DELIVER",
                    "CUSTOMER",
                    "VENDOR",
                    "INSPECTION",
                    "REPORT",
                    "NOTIFICATION",
                    "ORDERNO",
                    "URDERNO",
                    "MATERIAL",
                    "MATER1AL",
                    "MATL",
                ]

                # ------------------------------------------------
                # ZNAJOB
                # ------------------------------------------------
                znajob_match = re.search(
                    r"\b(ZNAJOB[A-Z0-9]*)\b",
                    full_text,
                    re.IGNORECASE
                )

                if znajob_match:

                    order_no = (
                        znajob_match
                        .group(1)
                        .strip()
                    )

                else:

                    # ------------------------------------------------
                    # MHXP + 2/3/4
                    # ------------------------------------------------
                    h_matches = re.findall(
                        r"\b([MHXP][234][A-Z0-9\-_]+)\b",
                        full_text,
                        re.IGNORECASE
                    )

                    for hm in h_matches:

                        hm_upper = hm.upper()

                        if (
                            hm_upper not in order_blacklist
                            and not hm_upper.startswith("MATER")
                            and not hm_upper.startswith("MI")
                            and not hm_upper.startswith("PO")
                            and not hm_upper.startswith("P0")
                        ):

                            order_no = hm.strip()

                            break

                    # ------------------------------------------------
                    # 수주번호 문구 기준 보조 검색
                    # ------------------------------------------------
                    if not order_no:

                        alt_order = re.search(
                            r"수주번호(?:[^\w]|Order|Urder|No)*"
                            r"([MHXP][234][A-Za-z0-9\-_]*)",
                            full_text,
                            re.IGNORECASE
                        )

                        if alt_order:

                            cand = (
                                alt_order
                                .group(1)
                                .strip()
                            )

                            cand_upper = cand.upper()

                            if (
                                cand_upper not in order_blacklist
                                and not cand_upper.startswith("MATER")
                                and not cand_upper.startswith("MI")
                                and not cand_upper.startswith("PO")
                                and not cand_upper.startswith("P0")
                            ):

                                order_no = cand

                # ------------------------------------------------
                # 끝의 - 또는 _ 제거
                # ------------------------------------------------
                order_no = re.sub(
                    r"[\-_]$",
                    "",
                    order_no
                )

                order_no = clean_and_fix_order_no(
                    order_no
                )

                # ==================================================
                # 2. 의뢰일자
                # ==================================================
                date = ""

                date_matches = re.findall(
                    r"(20[2-9][0-9][-/.][0-9]{2}[-/.][0-9]{2})",
                    full_text
                )

                if date_matches:

                    for m in date_matches:

                        digits = re.sub(
                            r"[^0-9]",
                            "",
                            m
                        )

                        if (
                            len(digits) == 8
                            and digits.startswith("20")
                        ):

                            date = digits

                            break

                # ------------------------------------------------
                # 보조 날짜 검색
                # ------------------------------------------------
                if not date:

                    for txt in full_text_list:

                        digits = re.sub(
                            r"[^0-9]",
                            "",
                            txt
                        )

                        if (
                            len(digits) == 8
                            and digits.startswith("20")
                        ):

                            date = digits

                            break

                # ==================================================
                # 3. 업체명 추출
                # ==================================================
                vendor = ""

                customer_words = set()

                if not df.empty and "text" in df.columns:

                    # ------------------------------------------------
                    # 고객명
                    # ------------------------------------------------
                    cust_labels = df[
                        df["text"]
                        .astype(str)
                        .str.contains(
                            "고객|Customer",
                            na=False,
                            case=False
                        )
                    ]

                    if not cust_labels.empty:

                        c_top = cust_labels.iloc[0]["top"]

                        c_left = cust_labels.iloc[0]["left"]

                        cust_targets = df[
                            (df["top"] >= c_top - 20)
                            &
                            (df["top"] <= c_top + 30)
                            &
                            (df["left"] > c_left)
                        ].sort_values(
                            by="left"
                        )

                        for _, r in cust_targets.iterrows():

                            clean_c = re.sub(
                                r"[^가-힣a-zA-Z0-9]",
                                "",
                                str(r["text"])
                            )

                            if (
                                clean_c
                                and clean_c not in [
                                    "고객",
                                    "Customer"
                                ]
                            ):

                                customer_words.add(
                                    clean_c
                                )

                    # ------------------------------------------------
                    # 업체 소재지 / Vendor
                    # ------------------------------------------------
                    vendor_labels = df[
                        df["text"]
                        .astype(str)
                        .str.contains(
                            "업체소재지|소재지|Vendor",
                            na=False,
                            case=False
                        )
                    ]

                    if not vendor_labels.empty:

                        v_row = vendor_labels.iloc[0]

                        v_top = v_row["top"]

                        v_left = v_row["left"]

                        targets = df[
                            (df["left"] > v_left + 5)
                            &
                            (df["top"] >= v_top - 40)
                            &
                            (df["top"] <= v_top + 50)
                        ].sort_values(
                            by="left"
                        )

                        for _, r in targets.iterrows():

                            t = str(r["text"])

                            # ------------------------------------------------
                            # 주소 / 불필요 항목 제외
                            # ------------------------------------------------
                            if any(
                                k in t
                                for k in [
                                    "업체소재지",
                                    "Vendor",
                                    "Address",
                                    "결재",
                                    "성산구",
                                    "의창구",
                                    "강서구",
                                    "녹산산업",
                                ]
                            ):
                                continue

                            clean_t = re.split(
                                r"[\(\[\d]"
                                r"|경상남도"
                                r"|창원시"
                                r"|의창구"
                                r"|부산"
                                r"|강서구"
                                r"|녹산"
                                r"|경남"
                                r"|서울"
                                r"|경기"
                                r"|시"
                                r"|구"
                                r"|군",
                                t,
                            )[0].strip()

                            clean_t = re.sub(
                                r"[^가-힣a-zA-Z0-9]",
                                "",
                                clean_t
                            )

                            if (
                                len(clean_t) >= 2
                                and clean_t not in customer_words
                            ):

                                vendor = clean_t

                                break

                # ------------------------------------------------
                # 업체명 보조 검색
                # ------------------------------------------------
                if not vendor:

                    for txt in full_text_list:

                        clean_txt = re.split(
                            r"[\(\[\d]"
                            r"|경상남도"
                            r"|창원시"
                            r"|의창구"
                            r"|부산"
                            r"|강서구"
                            r"|녹산"
                            r"|경남"
                            r"|서울"
                            r"|경기"
                            r"|시"
                            r"|구"
                            r"|군",
                            txt,
                        )[0].strip()

                        clean_txt = re.sub(
                            r"[^가-힣a-zA-Z0-9]",
                            "",
                            clean_txt
                        )

                        if clean_txt in customer_words:
                            continue

                        if clean_txt in [
                            "업체소재지",
                            "Vendor",
                            "Address",
                            "고객",
                            "Customer",
                        ]:
                            continue

                        if (
                            len(clean_txt) >= 2
                            and any(
                                k in txt
                                for k in [
                                    "스틸",
                                    "볼텍",
                                    "머티리얼",
                                    "에스앤피",
                                    "주식회사",
                                    "(주)",
                                    "공업",
                                    "금속",
                                    "테크",
                                    "산업",
                                    "엔지니어링",
                                    "상사",
                                    "정밀",
                                    "기업",
                                    "파이프",
                                    "금동",
                                    "스틱",
                                ]
                            )
                        ):

                            vendor = clean_txt

                            break

                # ------------------------------------------------
                # 업체명 OCR 오류 보정
                # ------------------------------------------------
                if vendor:

                    vendor = re.sub(
                        r"스틱$",
                        "스틸",
                        vendor
                    )

                    vendor = vendor.replace(
                        "스틱",
                        "스틸"
                    )

                # ==================================================
                # 4. 발주서번호
                # ==================================================
                po_no = ""

                po_match = re.search(
                    r"(PO?[0-9]{8,})",
                    full_text,
                    re.IGNORECASE
                )

                if po_match:

                    po_no = (
                        po_match
                        .group(1)
                        .strip()
                    )

                else:

                    alt_po = re.search(
                        r"발주서[^\w]*번호[^\w]*([A-Za-z0-9]+)",
                        full_text
                    )

                    if alt_po:

                        po_no = (
                            alt_po
                            .group(1)
                            .strip()
                        )

                # ==================================================
                # 표시용 값
                # ==================================================
                disp_order = (
                    order_no
                    if order_no
                    else "미인식"
                )

                disp_date = (
                    date
                    if date
                    else "미인식"
                )

                disp_vendor = (
                    vendor
                    if vendor
                    else "업체명확인필요"
                )

                disp_po = (
                    po_no
                    if po_no
                    else "미인식"
                )

                # ==================================================
                # 새 파일명
                # ==================================================
                new_filename = (
                    f"{disp_order}_"
                    f"{disp_date}_"
                    f"{disp_vendor}_"
                    f"{disp_po}."
                    f"{file_ext}"
                )

                # ==================================================
                # 결과 저장
                # ==================================================
                processed_results.append(
                    {
                        "original_name": file.name,
                        "new_name": new_filename,
                        "order_no": disp_order,
                        "date": disp_date,
                        "vendor": disp_vendor,
                        "po_no": disp_po,
                        "file_bytes": file_bytes,
                        "ext": file_ext,
                    }
                )

            except Exception as e:

                st.error(
                    f"'{file.name}' 처리 중 오류 발생: {e}"
                )

                st.exception(e)

            # ----------------------------------------------------
            # 진행률
            # ----------------------------------------------------
            prog_val = min(
                1.0,
                float(idx + 1)
                / float(len(target_files))
            )

            progress_bar.progress(
                prog_val
            )

    # ============================================================
    # 완료
    # ============================================================
    if uploaded_files:

        st.success(
            "🎉 모든 파일 분석이 완료되었습니다!"
        )

        st.markdown("---")

        st.markdown(
            "### 📊 파일별 상세 결과 및 개별 다운로드"
        )

        # ========================================================
        # 파일별 결과
        # ========================================================
        for idx, res in enumerate(
            processed_results
        ):

            with st.expander(
                f"📁 기존 파일: {res['original_name']} "
                f"➔ 변경: {res['new_name']}",
                expanded=True,
            ):

                col1, col2 = st.columns(
                    [3, 1]
                )

                # ------------------------------------------------
                # 인식 결과
                # ------------------------------------------------
                with col1:

                    st.write(
                        f"**수주번호:** `{res['order_no']}` | "
                        f"**의뢰일자:** `{res['date']}` | "
                        f"**업체명:** `{res['vendor']}` | "
                        f"**발주서번호:** `{res['po_no']}`"
                    )

                # ------------------------------------------------
                # 개별 다운로드
                # ------------------------------------------------
                with col2:

                    # PDF / 이미지 MIME 구분
                    if res["ext"] == "pdf":

                        mime_type = "application/pdf"

                    elif res["ext"] in [
                        "jpg",
                        "jpeg"
                    ]:

                        mime_type = "image/jpeg"

                    elif res["ext"] == "png":

                        mime_type = "image/png"

                    else:

                        mime_type = (
                            f"application/{res['ext']}"
                        )

                    st.download_button(
                        label="💾 변경된 파일 다운로드",
                        data=res["file_bytes"],
                        file_name=res["new_name"],
                        mime=mime_type,
                        key=f"dl_{idx}_{res['original_name']}",
                    )


# ============================================================
# 프로그램 실행
# ============================================================
if __name__ == "__main__":

    try:

        main()

    except Exception as e:

        import streamlit as st

        st.error(
            f"프로그램 구동 중 에러가 발생했습니다: {e}"
        )

        st.exception(e)