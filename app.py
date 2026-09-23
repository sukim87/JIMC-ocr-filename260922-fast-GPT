import io
import os
import re
import sys
import time
import easyocr
import numpy as np
import pandas as pd
import pypdfium2 as pdfium
import streamlit as st
from PIL import Image


# EXE 패키징 시 리소스 경로 리졸버 함수
def get_resource_path(relative_path):
    if hasattr(sys, '_MEIPASS'):
        return os.path.join(sys._MEIPASS, relative_path)
    return os.path.join(os.path.abspath('.'), relative_path)


def main():
    # 페이지 기본 설정
    st.set_page_config(
        page_title='(주)정우산기 | Jeongwoo AI-Doc Organizer (인수검사서 자동 분류기)',
        page_icon='📄',
        layout='wide',
        initial_sidebar_state='expanded',
    )

    # 🎨 정우산기 브랜드 컬러 (RED & WHITE) 및 가독성 강화 CSS 적용
    st.markdown(
        """
    <style>
    .main .block-container {
        padding-top: 1.5rem;
        padding-bottom: 3rem;
        max-width: 1000px;
    }
    
    .brand-header {
        background: linear-gradient(135deg, #C8102E 0%, #9B001C 100%);
        padding: 22px 28px;
        border-radius: 12px;
        color: #ffffff;
        box-shadow: 0 4px 15px rgba(200, 16, 46, 0.15);
        margin-bottom: 20px;
    }
    .brand-header h1 {
        color: #ffffff !important;
        font-size: 1.7rem !important;
        font-weight: 700 !important;
        margin: 0 !important;
        padding: 0 !important;
    }
    .brand-header p {
        color: #FFD2D7 !important;
        font-size: 0.88rem !important;
        margin-top: 6px !important;
        margin-bottom: 0 !important;
    }
    .version-tag {
        background-color: #ffffff;
        color: #C8102E;
        padding: 3px 10px;
        border-radius: 20px;
        font-size: 0.78rem;
        font-weight: 700;
        margin-left: 10px;
        vertical-align: middle;
    }

    .info-card {
        background-color: #FFFFFF;
        border: 1px solid #E2E8F0;
        border-left: 5px solid #C8102E;
        border-radius: 10px;
        padding: 18px 22px;
        margin-bottom: 20px;
        box-shadow: 0 2px 8px rgba(0,0,0,0.03);
    }

    /* 🎨 가독성 대폭 향상 - 표준 파일명 규칙 뱃지 (크기 확 키움) */
    .code-badge {
        background-color: #FFF1F2;
        color: #C8102E;
        border: 1.5px solid #FECDD3;
        padding: 6px 14px;
        border-radius: 8px;
        font-size: 1.15rem; /* 글자 크기 확대 */
        font-weight: 800;
        letter-spacing: 0.5px;
        display: inline-block;
        margin-top: 6px;
        font-family: 'Pretendard', 'Malgun Gothic', sans-serif;
        box-shadow: 0 1px 3px rgba(200, 16, 46, 0.08);
    }

    .speed-card {
        background-color: #FFF5F5;
        border: 1px solid #FFCDD2;
        border-radius: 10px;
        padding: 16px;
        text-align: center;
        height: 100%;
        display: flex;
        flex-direction: column;
        justify-content: center;
    }
    .speed-card-title {
        color: #C8102E;
        font-size: 1.05rem;
        font-weight: 700;
        margin-bottom: 6px;
    }
    .speed-card-desc {
        color: #4A5568;
        font-size: 0.83rem;
        line-height: 1.45;
        margin: 0;
    }

    div[data-testid="stFileUploader"] {
        background-color: #FFFFFF;
        border: 2px dashed #CBD5E1;
        border-radius: 12px;
        padding: 15px;
        transition: all 0.25s ease;
    }
    div[data-testid="stFileUploader"]:hover {
        border-color: #C8102E;
        background-color: #FFF8F8;
    }

    .sidebar-card {
        background-color: #FFFFFF;
        border-radius: 10px;
        padding: 16px;
        margin-top: 15px;
        border: 1px solid #E2E8F0;
        border-top: 3px solid #C8102E;
    }
    .sidebar-card h4 {
        color: #1E293B;
        font-size: 0.95rem;
        font-weight: 700;
        margin-bottom: 8px;
    }
    .sidebar-card p {
        color: #475569;
        font-size: 0.85rem;
        margin-bottom: 5px;
        line-height: 1.4;
    }
    </style>
    """,
        unsafe_allow_html=True,
    )

    # ---------------- 사이드바 (로고 및 담당자 문의 정보) ----------------
    with st.sidebar:
        logo_path = get_resource_path('logo.jpg')
        if not os.path.exists(logo_path):
            logo_path = get_resource_path('세로-영문-Jeongwoo.jpg')

        if os.path.exists(logo_path):
            try:
                st.image(logo_path, use_container_width=True)
            except Exception:
                pass

        st.markdown("""
            <div class="sidebar-card">
                <h4>📞 시스템 문의 및 지원</h4>
                <p><b>부서:</b> PS품질팀</p>
                <p><b>담당자:</b> 김선웅</p>
                <p style="margin-top: 8px; font-size:0.8rem; color:#64748B;">
                프로그램 오류, 수주번호/업체명 추출 규칙 변경 요청
                </p>
            </div>
            """, unsafe_allow_html=True)

        st.markdown('<div style="margin-top: 30px;"></div>', unsafe_allow_html=True)
        st.caption('ⓒ Jeongwoo Industrial Machine Co., Ltd. All rights reserved.')

    # ---------------- 메인 화면 고급 헤더 ----------------
    UPDATE_DATE = '2026-09-22'
    st.markdown(
        f"""
    <div class="brand-header">
        <h1>📄 Jeongwoo AI-Doc Organizer (인수검사서 자동 분류기) <span class="version-tag">v{UPDATE_DATE}</span></h1>
        <p>📅 최종 업데이트: {UPDATE_DATE} | (주)정우산기 품질관리 시스템</p>
    </div>
    """,
        unsafe_allow_html=True,
    )

    # ---------------- 사용 안내 카드 ----------------
    st.markdown(
        """
    <div class="info-card">
        <div style="font-weight: 700; color: #1E293B; margin-bottom: 10px; font-size: 1.05rem;">
            💡 스마트 안내
        </div>
        <ul style="padding-left: 18px; margin-bottom: 0; color: #334155; font-size: 0.95rem; line-height: 1.75;">
            <li>인수검사 완료 스캔 문서(PDF/이미지)를 올리시면 AI가 파일명을 자동 정돈합니다.</li>
            <li>기울어지거나 90도/180도 회전된 스캔본도 바르게 교정하여 인식합니다.</li>
            <li style="margin-top: 4px;"><b>표준 파일명 규칙:</b><br>
                <span class="code-badge">수주번호 _ 의뢰일자 _ 업체명 _ 발주서번호.pdf</span>
            </li>
        </ul>
    </div>
    """,
        unsafe_allow_html=True,
    )

    # ---------------- 📸 샘플 이미지 & 3배 속도 카드 ----------------
    sample_img_path = get_resource_path('example_sample.jpg')
    if not os.path.exists(sample_img_path):
        sample_img_path = get_resource_path('example_sample.png')

    col_img, col_tip = st.columns([1.8, 1.0], gap='medium')

    with col_img:
        if os.path.exists(sample_img_path):
            st.image(sample_img_path, caption='📌 올바른 세로 스캔 문서 예시', use_container_width=True)
        else:
            st.info("📌 예시 이미지를 폴더에 추가해 주세요.")

    with col_tip:
        st.markdown(
            """
        <div class="speed-card">
            <div class="speed-card-title">⚡ 분석 속도 3배 향상 팁!</div>
            <div class="speed-card-desc">
                예시처럼 <b>올바른 방향(세로)</b>으로 스캔하여 올리시면 AI 회전 교정 연산이 줄어들어 <b>처리 속도가 약 3배 빠릅니다.</b>
            </div>
        </div>
        """,
            unsafe_allow_html=True,
        )

    st.markdown("<div style='margin-bottom: 25px;'></div>", unsafe_allow_html=True)

    # EasyOCR 모델 리더 로드 (캐싱 처리)
    @st.cache_resource
    def load_ocr_reader():
        return easyocr.Reader(['ko', 'en'], gpu=False)

    with st.spinner('🤖 OCR AI 엔진을 초기화하는 중입니다...'):
        try:
            reader = load_ocr_reader()
        except Exception as e:
            st.error(f'OCR AI 모델 로딩 중 오류가 발생했습니다: {e}')
            st.exception(e)
            return

    def clean_and_fix_order_no(order_str):
        if not order_str:
            return ''

        order_upper = order_str.upper().strip()

        if (
            order_upper.startswith('PO')
            or order_upper.startswith('P0')
            or order_upper.startswith('MI')
        ):
            return ''
        if any(bad in order_upper for bad in ['MATERIAL', 'MATER1AL', 'MATL']):
            return ''

        if order_upper.startswith('ZNAJOB'):
            return order_str.strip()

        match = re.search(r'([MHXP][234][A-Za-z0-9\-_]+)', order_str, re.IGNORECASE)
        if not match:
            return ''

        raw_order = match.group(1)
        prefix = raw_order[0].upper()
        rest = raw_order[1:]

        parts = re.split(r'([\-_])', rest)
        main_part = parts[0]

        corrected_main = ''
        for idx, char in enumerate(main_part):
            c_upper = char.upper()
            if idx < 6:
                if c_upper in ['O', 'Q']:
                    corrected_main += '0'
                elif c_upper == 'Z':
                    corrected_main += '2'
                elif c_upper in ['I', 'L']:
                    corrected_main += '1'
                elif c_upper == 'S':
                    corrected_main += '5'
                elif c_upper == 'B':
                    corrected_main += '8'
                else:
                    corrected_main += char
            else:
                corrected_main += char

        parts[0] = corrected_main
        return prefix + ''.join(parts)

    def process_ocr_smart(img, ocr_reader):
        max_w = 2000
        w, h = img.size
        if w > max_w:
            new_h = int(h * (max_w / w))
            img = img.resize((max_w, new_h), Image.Resampling.LANCZOS)

        angles = [0, 90, 180, 270]
        best_angle = 0
        best_score = -1
        best_results = []
        best_img = img

        keywords = [
            '인수검사', '의뢰서', '보고서', '수주번호', '발주서',
            'INSPECTION', 'RECEIVING', 'NOTIFICATION', 'REPORT',
            'Order', 'Vendor', 'Customer', '품질', '구매'
        ]

        for angle in angles:
            test_img = img.rotate(angle, expand=True) if angle != 0 else img
            tw, th = test_img.size

            crop_box = (0, 0, tw, int(th * 0.65))
            cropped = test_img.crop(crop_box)
            img_np = np.array(cropped.convert('RGB'))

            results = ocr_reader.readtext(img_np)
            extracted_text = ' '.join([t[1].strip() for t in results])

            score = 0
            for kw in keywords:
                if kw.lower() in extracted_text.lower():
                    score += 15

            has_order_pattern = False
            if re.search(r'([MHXP][234][A-Z0-9]+|ZNAJOB)', extracted_text, re.IGNORECASE):
                score += 50
                has_order_pattern = True

            score += min(len(extracted_text), 20)

            if score > best_score:
                best_score = score
                best_angle = angle
                best_img = test_img
                best_results = results

            if angle == 0 and has_order_pattern and score >= 50:
                return best_results, best_img

        if best_score < 15:
            img_np = np.array(img.convert('RGB'))
            return ocr_reader.readtext(img_np), img

        return best_results, best_img

    # ---------------- 파일 업로드 ----------------
    st.subheader('📁 검사서 파일 업로드')
    uploaded_files = st.file_uploader(
        '변환할 PDF 또는 이미지 파일(PNG, JPG)을 이곳에 끌어다 놓으세요. (최대 5개)',
        type=['pdf', 'png', 'jpg', 'jpeg'],
        accept_multiple_files=True,
    )

    if uploaded_files:
        if len(uploaded_files) > 5:
            st.warning('⚠️ 최대 5개까지 한 번에 처리 가능합니다. 상위 5개 파일만 분석합니다.')
            target_files = uploaded_files[:5]
        else:
            target_files = uploaded_files

        start_time = time.time()
        processed_results = []

        # ☕ 로딩 멘트에 커피 한 잔의 여유 재치 문구 적용
        with st.spinner('☕ AI가 문서 내용을 정밀 분석 중입니다... 따뜻한 커피 한 잔의 여유를 가져보세요! ☕✨'):
            for idx, file in enumerate(target_files):
                file.seek(0)
                file_bytes = file.read()

                if not file_bytes:
                    continue

                file_ext = file.name.split('.')[-1].lower() if '.' in file.name else 'pdf'

                try:
                    image = None
                    if file_ext == 'pdf':
                        pdf = pdfium.PdfDocument(file_bytes)
                        page = pdf[0]
                        image = page.render(scale=1.6).to_pil()
                        pdf.close()
                    else:
                        image = Image.open(io.BytesIO(file_bytes))

                    full_text = ''
                    df = pd.DataFrame()

                    if image:
                        ocr_results, _ = process_ocr_smart(image, reader)

                        parsed_data = []
                        full_text_list = []

                        for bbox, text, prob in ocr_results:
                            text_clean = str(text).strip()
                            if text_clean:
                                full_text_list.append(text_clean)
                                top_y = bbox[0][1]
                                left_x = bbox[0][0]
                                parsed_data.append({
                                    'text': text_clean,
                                    'top': top_y,
                                    'left': left_x,
                                    'prob': prob,
                                })

                        full_text = ' '.join(full_text_list)
                        df = pd.DataFrame(parsed_data) if parsed_data else pd.DataFrame()

                    # 1. 수주번호 추출
                    order_no = ''
                    order_blacklist = [
                        'ORDER', 'URDER', 'NUMBER', 'DELIVER', 'CUSTOMER',
                        'VENDOR', 'INSPECTION', 'REPORT', 'NOTIFICATION',
                        'ORDERNO', 'URDERNO', 'MATERIAL', 'MATER1AL', 'MATL'
                    ]

                    znajob_match = re.search(r'\b(ZNAJOB[A-Z0-9]*)\b', full_text, re.IGNORECASE)
                    if znajob_match:
                        order_no = znajob_match.group(1).strip()
                    else:
                        h_matches = re.findall(r'\b([MHXP][234][A-Z0-9\-_]+)\b', full_text, re.IGNORECASE)
                        for hm in h_matches:
                            hm_upper = hm.upper()
                            if (
                                hm_upper not in order_blacklist
                                and not hm_upper.startswith('MATER')
                                and not hm_upper.startswith('MI')
                                and not hm_upper.startswith('PO')
                                and not hm_upper.startswith('P0')
                            ):
                                order_no = hm.strip()
                                break

                        if not order_no:
                            alt_order = re.search(
                                r'수주번호(?:[^\w]|Order|Urder|No)*([MHXP][234][A-Za-z0-9\-_]*)',
                                full_text,
                                re.IGNORECASE,
                            )
                            if alt_order:
                                cand = alt_order.group(1).strip()
                                cand_upper = cand.upper()
                                if (
                                    cand_upper not in order_blacklist
                                    and not cand_upper.startswith('MATER')
                                    and not cand_upper.startswith('MI')
                                    and not cand_upper.startswith('PO')
                                    and not cand_upper.startswith('P0')
                                ):
                                    order_no = cand

                    order_no = re.sub(r'[\-_]$', '', order_no)
                    order_no = clean_and_fix_order_no(order_no)

                    # 2. 의뢰일자 추출
                    date = ''
                    date_matches = re.findall(r'(20[2-9][0-9][-/.][0-9]{2}[-/.][0-9]{2})', full_text)
                    if date_matches:
                        for m in date_matches:
                            digits = re.sub(r'[^0-9]', '', m)
                            if len(digits) == 8 and digits.startswith('20'):
                                date = digits
                                break
                    if not date:
                        for txt in full_text_list:
                            digits = re.sub(r'[^0-9]', '', txt)
                            if len(digits) == 8 and digits.startswith('20'):
                                date = digits
                                break

                    # 3. 업체명 추출
                    vendor = ''
                    customer_words = set()
                    if not df.empty and 'text' in df.columns:
                        cust_labels = df[
                            df['text']
                            .astype(str)
                            .str.contains('고객|Customer', na=False, case=False)
                        ]
                        if not cust_labels.empty:
                            c_top, c_left = (
                                cust_labels.iloc[0]['top'],
                                cust_labels.iloc[0]['left'],
                            )
                            cust_targets = df[
                                (df['top'] >= c_top - 20)
                                & (df['top'] <= c_top + 30)
                                & (df['left'] > c_left)
                            ].sort_values(by='left')
                            for _, r in cust_targets.iterrows():
                                clean_c = re.sub(r'[^가-힣a-zA-Z0-9]', '', str(r['text']))
                                if clean_c and clean_c not in ['고객', 'Customer']:
                                    customer_words.add(clean_c)

                        vendor_labels = df[
                            df['text']
                            .astype(str)
                            .str.contains('업체소재지|소재지|Vendor', na=False, case=False)
                        ]
                        if not vendor_labels.empty:
                            v_row = vendor_labels.iloc[0]
                            v_top, v_left = v_row['top'], v_row['left']
                            targets = df[
                                (df['left'] > v_left + 5)
                                & (df['top'] >= v_top - 40)
                                & (df['top'] <= v_top + 50)
                            ].sort_values(by='left')
                            for _, r in targets.iterrows():
                                t = str(r['text'])
                                if any(
                                    k in t
                                    for k in [
                                        '업체소재지', '소재지', 'Vendor', 'Address',
                                        '결재', '성산구', '의창구', '강서구', '녹산산업'
                                    ]
                                ):
                                    continue
                                clean_t = re.split(
                                    r'[\(\[\d]|경상남도|창원시|의창구|부산|강서구|녹산|경남|서울|경기|시|구|군',
                                    t,
                                )[0].strip()
                                clean_t = re.sub(r'[^가-힣a-zA-Z0-9]', '', clean_t)
                                if (
                                    len(clean_t) >= 2
                                    and clean_t not in customer_words
                                    and clean_t not in ['업체소재지', '소재지']
                                ):
                                    vendor = clean_t
                                    break

                    if not vendor:
                        for txt in full_text_list:
                            clean_txt = re.split(
                                r'[\(\[\d]|경상남도|창원시|의창구|부산|강서구|녹산|경남|서울|경기|시|구|군',
                                txt,
                            )[0].strip()
                            clean_txt = re.sub(r'[^가-힣a-zA-Z0-9]', '', clean_txt)
                            if clean_txt in customer_words or clean_txt in [
                                '업체소재지', '소재지', 'Vendor', 'Address', '고객', 'Customer'
                            ]:
                                continue
                            if len(clean_txt) >= 2 and any(
                                k in txt
                                for k in [
                                    '스틸', '볼텍', '머티리얼', '에스앤피', '주식회사',
                                    '(주)', '공업', '금속', '테크', '산업', '엔지니어링',
                                    '상사', '정밀', '기업', '파이프', '금동', '스틱', '상사'
                                ]
                            ):
                                vendor = clean_txt
                                break

                    if vendor:
                        vendor = re.sub(r'^업체소재지', '', vendor).strip()
                        vendor = re.sub(r'스틱$', '스틸', vendor)
                        vendor = vendor.replace('스틱', '스틸')

                    # 4. 발주서번호(PO No.) 정밀 추출 보강
                    po_no = ''
                    if not df.empty and 'text' in df.columns:
                        po_labels = df[
                            df['text']
                            .astype(str)
                            .str.contains('발주서|Deliver|Po|P.O', na=False, case=False)
                        ]
                        if not po_labels.empty:
                            p_row = po_labels.iloc[0]
                            p_top, p_left = p_row['top'], p_row['left']
                            po_targets = df[
                                (df['top'] >= p_top - 30)
                                & (df['top'] <= p_top + 60)
                                & (df['left'] >= p_left - 20)
                            ].sort_values(by='top')
                            
                            for _, r in po_targets.iterrows():
                                raw_p = str(r['text']).strip()
                                match_cand = re.search(r'([A-Za-z0-9\-_]{6,16})', raw_p)
                                if match_cand:
                                    cand_str = match_cand.group(1).strip()
                                    cand_upper = cand_str.upper()
                                    if (
                                        cand_upper not in ['DELIVER', 'DELIVERNO', 'INSPECTION', 'REPORT', 'NO', 'NUMBER']
                                        and cand_str != order_no
                                    ):
                                        po_no = cand_str
                                        break

                    if not po_no:
                        po_pattern = re.search(r'\b((?:PO|P0|MI)[A-Za-z0-9\-_]{6,14})\b', full_text, re.IGNORECASE)
                        if po_pattern:
                            po_no = po_pattern.group(1).strip()
                        else:
                            alt_po = re.search(r'(?:발주서|PO|P\.O|Deliver)*(?:[^\w]|번호|No)*([A-Za-z0-9\-_]{7,15})', full_text, re.IGNORECASE)
                            if alt_po:
                                cand = alt_po.group(1).strip()
                                if cand != order_no and cand.upper() not in ['INSPECTION', 'RECEIVING', 'NOTIFICATION']:
                                    po_no = cand

                    disp_order = order_no if order_no else '미인식'
                    disp_date = date if date else '미인식'
                    disp_vendor = vendor if vendor else '업체명확인필요'
                    disp_po = po_no if po_no else '미인식'

                    new_filename = (
                        f'{disp_order}_{disp_date}_{disp_vendor}_{disp_po}.{file_ext}'
                    )

                    processed_results.append({
                        'original_name': file.name,
                        'new_name': new_filename,
                        'order_no': disp_order,
                        'date': disp_date,
                        'vendor': disp_vendor,
                        'po_no': disp_po,
                        'file_bytes': file_bytes,
                        'ext': file_ext,
                    })

                except Exception as e:
                    st.error(f"'{file.name}' 처리 중 오류 발생: {e}")
                    st.exception(e)

        elapsed_time = time.time() - start_time

        st.success(
            '🎉 모든 파일 분석이 완료되었습니다!'
            f' **(⏱️ 총 작업 소요 시간: {elapsed_time:.1f}초)**'
        )

        # ---------------- 개별 다운로드 결과 리포트 영역 ----------------
        st.markdown('---')
        st.markdown('### 📊 분석 결과 리포트 및 개별 파일 다운로드')

        for idx, res in enumerate(processed_results):
            with st.expander(
                f"📁 {res['original_name']}  ➔  ✨ {res['new_name']}", expanded=True
            ):
                col1, col2 = st.columns([3, 1])
                with col1:
                    st.markdown(f"""
                        * **수주번호:** `{res['order_no']}`
                        * **의뢰일자:** `{res['date']}`
                        * **업 체 명:** `{res['vendor']}`
                        * **발주번호:** `{res['po_no']}`
                        """)
                with col2:
                    st.download_button(
                        label='💾 변경된 파일 다운로드',
                        data=res['file_bytes'],
                        file_name=res['new_name'],
                        mime=f"application/{res['ext']}",
                        key=f"dl_{idx}_{res['original_name']}",
                        type='primary',
                    )


if __name__ == '__main__':
    try:
        main()
    except Exception as e:
        import streamlit as st

        st.error(f'프로그램 구동 중 에러가 발생했습니다: {e}')
        st.exception(e)
