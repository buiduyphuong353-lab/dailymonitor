# =====================================================================
# PHẦN 1: CẤU HÌNH & KHỞI TẠO CÁC THÔNG SỐ CƠ BẢN
# =====================================================================
import streamlit as st
import numpy as np
import json
from datetime import datetime
import matplotlib.pyplot as plt

# Từ điển chứa các quy tắc chung cho toàn bộ hệ thống
CAU_HINH_QUY_TAC = {
    "GIAY_TUOI_TOI_THIEU": 20,     # Lọc bỏ các lần bật máy bơm bị nhiễu (dưới 20 giây)
    "GIAY_TUOI_TOI_DA": 3600,      # Lọc bỏ các lần quên tắt máy bơm (trên 1 tiếng)
    "SO_NGAY_NGHI_TOI_DA": 2,      # Nếu dữ liệu rớt dưới ngưỡng quá 2 ngày thì coi như kết thúc vụ mùa đó
    "SO_NGAY_TOI_THIEU_MOT_VU": 7  # Một vụ mùa phải kéo dài ít nhất 7 ngày mới được tính là hợp lệ
}

# =====================================================================
# PHẦN 2: CÁC HÀM XỬ LÝ DỮ LIỆU CỐT LÕI
# =====================================================================

def lay_gia_tri_so_thuc_tu_chuoi(dong_du_lieu, danh_sach_tu_khoa):
    """
    Hàm này giúp tìm và chuyển đổi các con số có dấu phẩy (kiểu Việt Nam) 
    thành dấu chấm (kiểu Quốc tế để máy tính hiểu được).
    """
    for tu_khoa in danh_sach_tu_khoa:
        gia_tri_tim_thay = dong_du_lieu.get(tu_khoa)
        if gia_tri_tim_thay is not None:
            try:
                # Thay dấu phẩy thành dấu chấm rồi ép kiểu sang số thập phân (float)
                chuoi_gia_tri = str(gia_tri_tim_thay).replace(',', '.')
                return float(chuoi_gia_tri)
            except (ValueError, TypeError):
                continue
    return None

def tao_so_cai_du_lieu_tong_hop(danh_sach_tep_tin_nho_giot, danh_sach_tep_tin_cham_phan, khu_vuc_duoc_chon):
    """
    BƯỚC 1: Hợp nhất dữ liệu từ 2 loại tệp tin thành 1 bảng Sổ Cái duy nhất theo từng ngày.
    - Tệp Nhỏ giọt: Cung cấp Số lần tưới, Thời gian tưới, và EC Trung bình (TBEC).
    - Tệp Châm phân: Chỉ cung cấp EC Yêu cầu.
    """
    du_lieu_tam_thoi_theo_ngay = {}

    # ---------------------------------------------------------
    # GIAI ĐOẠN 1: ĐỌC VÀ LẤY DỮ LIỆU TỪ TỆP TIN NHỎ GIỌT
    # ---------------------------------------------------------
    if danh_sach_tep_tin_nho_giot:
        toan_bo_du_lieu_nho_giot = []
        # Gom tất cả các file nhỏ giọt lại với nhau
        for tep_tin in danh_sach_tep_tin_nho_giot:
            tep_tin.seek(0)
            toan_bo_du_lieu_nho_giot.extend(json.load(tep_tin))
        
        # Chỉ giữ lại dữ liệu của khu vực người dùng đã chọn và sắp xếp theo thời gian
        du_lieu_nho_giot_da_loc = [dong for dong in toan_bo_du_lieu_nho_giot if str(dong.get('STT')) == khu_vuc_duoc_chon]
        du_lieu_nho_giot_da_loc.sort(key=lambda x: x['Thời gian'])

        # Quét lần 1: Nhặt số liệu TBEC (EC trung bình) của từng dòng
        for dong_du_lieu in du_lieu_nho_giot_da_loc:
            try:
                thoi_diem = datetime.strptime(dong_du_lieu['Thời gian'], "%Y-%m-%d %H-%M-%S")
                ngay_dinh_dang_chuoi = thoi_diem.strftime("%Y-%m-%d")
            except:
                continue # Nếu lỗi định dạng thời gian thì bỏ qua dòng này
                
            # Tạo ô trống cho ngày mới nếu ngày này chưa tồn tại trong danh sách
            if ngay_dinh_dang_chuoi not in du_lieu_tam_thoi_theo_ngay: 
                du_lieu_tam_thoi_theo_ngay[ngay_dinh_dang_chuoi] = {
                    'so_lan_tuoi': 0, 
                    'tong_so_giay_tuoi': 0, 
                    'danh_sach_tbec': [], 
                    'danh_sach_ec_yeu_cau': []
                }
                
            # Tìm và cất giá trị TBEC vào danh sách chờ tính trung bình
            gia_tri_tbec = lay_gia_tri_so_thuc_tu_chuoi(dong_du_lieu, ['TBEC', 'tbec'])
            if gia_tri_tbec is not None: 
                du_lieu_tam_thoi_theo_ngay[ngay_dinh_dang_chuoi]['danh_sach_tbec'].append(gia_tri_tbec)

        # Quét lần 2: Đếm số lần Bật/Tắt và cộng dồn thời gian tưới
        for vi_tri in range(len(du_lieu_nho_giot_da_loc) - 1):
            dong_hien_tai = du_lieu_nho_giot_da_loc[vi_tri]
            dong_tiep_theo = du_lieu_nho_giot_da_loc[vi_tri + 1]
            
            if dong_hien_tai.get('Trạng thái') == "Bật" and dong_tiep_theo.get('Trạng thái') == "Tắt":
                thoi_diem_bat_dau = datetime.strptime(dong_hien_tai['Thời gian'], "%Y-%m-%d %H-%M-%S")
                thoi_diem_ket_thuc = datetime.strptime(dong_tiep_theo['Thời gian'], "%Y-%m-%d %H-%M-%S")
                so_giay_tuoi_thuc_te = (thoi_diem_ket_thuc - thoi_diem_bat_dau).total_seconds()
                
                # Chỉ tính những lần tưới hợp lệ (không quá ngắn, không quá dài)
                if CAU_HINH_QUY_TAC["GIAY_TUOI_TOI_THIEU"] <= so_giay_tuoi_thuc_te <= CAU_HINH_QUY_TAC["GIAY_TUOI_TOI_DA"]:
                    ngay_dinh_dang_chuoi = thoi_diem_bat_dau.strftime("%Y-%m-%d")
                    
                    if ngay_dinh_dang_chuoi not in du_lieu_tam_thoi_theo_ngay: 
                        du_lieu_tam_thoi_theo_ngay[ngay_dinh_dang_chuoi] = {'so_lan_tuoi': 0, 'tong_so_giay_tuoi': 0, 'danh_sach_tbec': [], 'danh_sach_ec_yeu_cau': []}
                    
                    du_lieu_tam_thoi_theo_ngay[ngay_dinh_dang_chuoi]['so_lan_tuoi'] += 1
                    du_lieu_tam_thoi_theo_ngay[ngay_dinh_dang_chuoi]['tong_so_giay_tuoi'] += so_giay_tuoi_thuc_te

    # ---------------------------------------------------------
    # GIAI ĐOẠN 2: ĐỌC VÀ LẤY DỮ LIỆU TỪ TỆP TIN CHÂM PHÂN
    # ---------------------------------------------------------
    if danh_sach_tep_tin_cham_phan:
        for tep_tin in danh_sach_tep_tin_cham_phan:
            tep_tin.seek(0)
            for dong_du_lieu in json.load(tep_tin):
                if str(dong_du_lieu.get('STT')) != khu_vuc_duoc_chon: 
                    continue # Bỏ qua nếu không đúng khu vực
                
                try:
                    thoi_diem = datetime.strptime(dong_du_lieu['Thời gian'], "%Y-%m-%d %H-%M-%S")
                    ngay_dinh_dang_chuoi = thoi_diem.strftime("%Y-%m-%d")
                except:
                    continue
                
                if ngay_dinh_dang_chuoi not in du_lieu_tam_thoi_theo_ngay: 
                    du_lieu_tam_thoi_theo_ngay[ngay_dinh_dang_chuoi] = {'so_lan_tuoi': 0, 'tong_so_giay_tuoi': 0, 'danh_sach_tbec': [], 'danh_sach_ec_yeu_cau': []}
                
                # CHỈ nhặt giá trị EC Yêu cầu, bỏ qua tất cả các thông số khác
                gia_tri_ec_yeu_cau = lay_gia_tri_so_thuc_tu_chuoi(dong_du_lieu, ['EC yêu cầu', 'ecreq'])
                if gia_tri_ec_yeu_cau is not None: 
                    du_lieu_tam_thoi_theo_ngay[ngay_dinh_dang_chuoi]['danh_sach_ec_yeu_cau'].append(gia_tri_ec_yeu_cau)

    # ---------------------------------------------------------
    # GIAI ĐOẠN 3: TÍNH TRUNG BÌNH VÀ CHỐT SỔ CÁI
    # ---------------------------------------------------------
    so_cai_chinh_thuc = {}
    for ngay_dang_xet, du_lieu_trong_ngay in du_lieu_tam_thoi_theo_ngay.items():
        so_cai_chinh_thuc[ngay_dang_xet] = {
            'so_lan_tuoi': du_lieu_trong_ngay['so_lan_tuoi'],
            # Đổi từ giây sang phút và làm tròn số
            'thoi_gian_tuoi_phut': int(round(du_lieu_trong_ngay['tong_so_giay_tuoi'] / 60)),
            
            # Tính trung bình TBEC trong ngày (nếu có dữ liệu)
            'tbec': float(f"{np.mean(du_lieu_trong_ngay['danh_sach_tbec']):.2f}") if du_lieu_trong_ngay['danh_sach_tbec'] else 0.0,
            
            # Tính trung bình EC Yêu cầu trong ngày (nếu có dữ liệu)
            'ec_yeu_cau': float(f"{np.mean(du_lieu_trong_ngay['danh_sach_ec_yeu_cau']):.2f}") if du_lieu_trong_ngay['danh_sach_ec_yeu_cau'] else 0.0
        }
    return so_cai_chinh_thuc

def tim_kiem_cac_mua_vu(so_cai_du_lieu, ten_chi_so_lam_goc, nguong_gia_tri_bat_dau):
    """
    BƯỚC 2: Nhận diện các mùa vụ.
    Thuật toán sẽ tìm những chuỗi ngày liên tiếp mà giá trị (Lần tưới hoặc EC) vượt qua mức ngưỡng quy định.
    """
    danh_sach_ngay_vuot_nguong = []
    
    # Gom tất cả các ngày đạt chuẩn vào một danh sách
    for chuoi_ngay, du_lieu in so_cai_du_lieu.items():
        if du_lieu[ten_chi_so_lam_goc] >= nguong_gia_tri_bat_dau:
            ngay_kieu_thoi_gian = datetime.strptime(chuoi_ngay, "%Y-%m-%d").date()
            danh_sach_ngay_vuot_nguong.append(ngay_kieu_thoi_gian)
            
    danh_sach_ngay_vuot_nguong.sort()
    danh_sach_cac_mua_vu = []
    
    if danh_sach_ngay_vuot_nguong:
        ngay_bat_dau_vu_hien_tai = danh_sach_ngay_vuot_nguong[0]
        
        for vi_tri in range(1, len(danh_sach_ngay_vuot_nguong)):
            ngay_dang_xet = danh_sach_ngay_vuot_nguong[vi_tri]
            ngay_lien_truoc = danh_sach_ngay_vuot_nguong[vi_tri - 1]
            khoang_cach_giua_hai_ngay = (ngay_dang_xet - ngay_lien_truoc).days
            
            # Nếu khoảng cách lớn hơn số ngày nghỉ tối đa -> Cắt vụ mùa
            if khoang_cach_giua_hai_ngay > CAU_HINH_QUY_TAC["SO_NGAY_NGHI_TOI_DA"]: 
                do_dai_cua_vu_vua_qua = (ngay_lien_truoc - ngay_bat_dau_vu_hien_tai).days + 1
                
                # Chỉ lưu lại nếu vụ mùa đó đủ dài (tránh dữ liệu rác)
                if do_dai_cua_vu_vua_qua >= CAU_HINH_QUY_TAC["SO_NGAY_TOI_THIEU_MOT_VU"]:
                    danh_sach_cac_mua_vu.append((ngay_bat_dau_vu_hien_tai, ngay_lien_truoc))
                
                # Khởi động lại ngày bắt đầu cho vụ mùa tiếp theo
                ngay_bat_dau_vu_hien_tai = ngay_dang_xet 
                
        # Xử lý đoạn đuôi (vụ mùa cuối cùng trong danh sách)
        ngay_cuoi_cung = danh_sach_ngay_vuot_nguong[-1]
        if (ngay_cuoi_cung - ngay_bat_dau_vu_hien_tai).days + 1 >= CAU_HINH_QUY_TAC["SO_NGAY_TOI_THIEU_MOT_VU"]:
            danh_sach_cac_mua_vu.append((ngay_bat_dau_vu_hien_tai, ngay_cuoi_cung))
            
    return danh_sach_cac_mua_vu

def chia_nho_mua_vu_thanh_cac_giai_doan(danh_sach_ngay_trong_vu, so_cai_du_lieu, ten_chi_so_lam_goc, sai_so_cho_phep):
    """
    BƯỚC 3: Cắt nhỏ vụ mùa thành các giai đoạn sinh trưởng.
    Dựa vào bước nhảy (sự chênh lệch) của chỉ số gốc. Nếu ngày hôm nay chênh lệch quá nhiều so với 
    ngày đầu tiên của giai đoạn hiện tại, hệ thống sẽ chốt giai đoạn đó và mở giai đoạn mới.
    """
    if not danh_sach_ngay_trong_vu: 
        return []
    
    danh_sach_cac_giai_doan_hoan_thien = []
    giai_doan_hien_tai = [danh_sach_ngay_trong_vu[0]]
    
    for vi_tri in range(1, len(danh_sach_ngay_trong_vu)):
        ngay_dang_xet = danh_sach_ngay_trong_vu[vi_tri]
        ngay_moc_cua_giai_doan = giai_doan_hien_tai[0] 
        
        gia_tri_cua_ngay_dang_xet = so_cai_du_lieu[ngay_dang_xet].get(ten_chi_so_lam_goc, 0)
        gia_tri_cua_ngay_moc = so_cai_du_lieu[ngay_moc_cua_giai_doan].get(ten_chi_so_lam_goc, 0)
        
        # Nếu mức chênh lệch lớn hơn sai số cho phép -> Cắt giai đoạn
        if abs(gia_tri_cua_ngay_dang_xet - gia_tri_cua_ngay_moc) >= sai_so_cho_phep:
            danh_sach_cac_giai_doan_hoan_thien.append(giai_doan_hien_tai)
            giai_doan_hien_tai = [ngay_dang_xet] # Mở giai đoạn mới với ngày hiện tại làm mốc
        else:
            giai_doan_hien_tai.append(ngay_dang_xet)
            
    # Lưu lại giai đoạn cuối cùng
    danh_sach_cac_giai_doan_hoan_thien.append(giai_doan_hien_tai)
    return danh_sach_cac_giai_doan_hoan_thien

# =====================================================================
# PHẦN 3: HÀM VẼ BIỂU ĐỒ TRỰC QUAN
# =====================================================================

def ve_bieu_do_tong_quan_cac_chi_so(du_lieu_tong_hop, danh_sach_cac_giai_doan):
    # Danh sách các chỉ số muốn vẽ lên màn hình
    danh_sach_chi_so_can_ve = [
        ("Số Lần Tưới", "so_lan_tuoi"), 
        ("EC Trung Bình (TBEC)", "tbec"), 
        ("EC Yêu Cầu", "ec_yeu_cau")
    ]
    
    # Tạo khung tranh gồm 3 biểu đồ xếp dọc
    khung_tranh, danh_sach_truc_toa_do = plt.subplots(3, 1, figsize=(16, 12), sharex=True)
    
    # Nối tất cả các ngày lại để tạo trục ngang (Trục X)
    danh_sach_ngay_thuc_te_de_ve = []
    for giai_doan in danh_sach_cac_giai_doan: 
        danh_sach_ngay_thuc_te_de_ve.extend(giai_doan)
        
    truc_x_duoi_dang_so_dem = np.arange(len(danh_sach_ngay_thuc_te_de_ve))
    
    # Vẽ lần lượt 3 biểu đồ
    for vi_tri, (ten_hien_thi_tren_bieu_do, ten_bien_trong_so_cai) in enumerate(danh_sach_chi_so_can_ve):
        truc_toa_do_hien_tai = danh_sach_truc_toa_do[vi_tri]
        du_lieu_doc_truc_y = [du_lieu_tong_hop[ngay][ten_bien_trong_so_cai] for ngay in danh_sach_ngay_thuc_te_de_ve]
        
        # Đặt màu sắc khác nhau cho từng biểu đồ cho dễ nhìn
        mau_sac = 'skyblue' if vi_tri == 0 else ('lightgreen' if vi_tri == 1 else 'salmon')
        
        truc_toa_do_hien_tai.bar(truc_x_duoi_dang_so_dem, du_lieu_doc_truc_y, color=mau_sac, edgecolor='black')
        truc_toa_do_hien_tai.set_ylabel(ten_hien_thi_tren_bieu_do, fontsize=12)
        truc_toa_do_hien_tai.grid(axis='y', linestyle='--', alpha=0.7)
        
        # Vẽ các đường kẻ dọc màu đỏ để ngăn cách các giai đoạn
        if len(danh_sach_cac_giai_doan) > 1:
            for giai_doan in danh_sach_cac_giai_doan[:-1]:
                vi_tri_cat_giai_doan = danh_sach_ngay_thuc_te_de_ve.index(giai_doan[-1]) 
                truc_toa_do_hien_tai.axvline(x=vi_tri_cat_giai_doan + 0.5, color='red', linestyle='-', linewidth=2.5)

    # Hiển thị ngày tháng ở trục dưới cùng (giảm bớt số lượng nhãn để không bị rối mắt)
    buoc_nhay_hien_thi_nhan = max(1, len(danh_sach_ngay_thuc_te_de_ve) // 30) 
    danh_sach_vi_tri_dat_nhan = truc_x_duoi_dang_so_dem[::buoc_nhay_hien_thi_nhan]
    danh_sach_nhan_ngay_thang = [danh_sach_ngay_thuc_te_de_ve[i][-5:] for i in danh_sach_vi_tri_dat_nhan]
    
    plt.xticks(danh_sach_vi_tri_dat_nhan, danh_sach_nhan_ngay_thang, rotation=45, ha='right', fontsize=10)
    khung_tranh.subplots_adjust(hspace=0.3) 
    
    return khung_tranh

# =====================================================================
# PHẦN 4: GIAO DIỆN NGƯỜI DÙNG CHÍNH (STREAMLIT)
# =====================================================================

def main():
    st.set_page_config(page_title="Phân Tích Dữ Liệu Nông Nghiệp", layout="wide")
    st.title("📊 Hệ Thống Phân Tích Logic Hợp Nhất Dữ Liệu")
    
    # Khu vực cột bên trái (Menu điều khiển)
    with st.sidebar:
        st.header("📂 1. Tải Tệp Tin Dữ Liệu")
        tep_tin_nho_giot = st.file_uploader("Tải lên tệp Nhỏ giọt (JSON)", accept_multiple_files=True, type=['json'])
        tep_tin_cham_phan = st.file_uploader("Tải lên tệp Châm phân (JSON)", accept_multiple_files=True, type=['json'])
        khu_vuc_chuyen_doi = st.selectbox("Chọn khu vực cần phân tích", ["1", "2", "3", "4"])
        
        st.markdown("---")
        st.header("⚙️ 2. Cài Đặt Thuật Toán Cắt Giai Đoạn")
        st.caption("Hệ thống sẽ dùng 1 chỉ số làm mốc để chia giai đoạn.")
        
        tu_dien_chi_so_dieu_khien = {"Lần tưới": "so_lan_tuoi", "TBEC": "tbec", "EC Yêu cầu": "ec_yeu_cau"}
        ten_chi_so_hien_thi = st.selectbox("🎯 Chọn Chỉ số làm Mốc", list(tu_dien_chi_so_dieu_khien.keys()))
        ten_bien_chi_so_goc = tu_dien_chi_so_dieu_khien[ten_chi_so_hien_thi]
        
        # Tự động gợi ý các mức cấu hình phù hợp tùy theo chỉ số được chọn
        if ten_bien_chi_so_goc == "so_lan_tuoi":
            gia_tri_nguong_goi_y = 5.0
            gia_tri_sai_so_goi_y = 2.0
        else:
            gia_tri_nguong_goi_y = 0.5
            gia_tri_sai_so_goi_y = 0.3
            
        nguong_bat_dau_vu = st.number_input(f"📈 Ngưỡng Bắt Đầu Vụ ({ten_chi_so_hien_thi})", value=gia_tri_nguong_goi_y, step=0.1)
        sai_so_cat_giai_doan = st.number_input(f"✂️ Sai Số Cắt GĐ ({ten_chi_so_hien_thi})", value=gia_tri_sai_so_goi_y, step=0.1)

    # ---------------------------------------------------------
    # LUỒNG XỬ LÝ CHÍNH KHI NGƯỜI DÙNG ĐÃ TẢI FILE
    # ---------------------------------------------------------
    if tep_tin_nho_giot and tep_tin_cham_phan:
        
        # BƯỚC 1: Lập Sổ Cái
        so_cai_du_lieu_hoan_chinh = tao_so_cai_du_lieu_tong_hop(tep_tin_nho_giot, tep_tin_cham_phan, khu_vuc_chuyen_doi)
        if not so_cai_du_lieu_hoan_chinh:
            st.error("❌ Không tìm thấy dữ liệu cho khu vực này trong các tệp đã tải lên.")
            return
            
        # BƯỚC 2: Tìm Mùa Vụ
        danh_sach_cac_mua_vu = tim_kiem_cac_mua_vu(so_cai_du_lieu_hoan_chinh, ten_bien_chi_so_goc, nguong_bat_dau_vu)
        
        if not danh_sach_cac_mua_vu:
            st.warning(f"⚠️ Không tìm thấy vụ nào có {ten_chi_so_hien_thi} vượt qua mức ngưỡng {nguong_bat_dau_vu} liên tục trên 7 ngày.")
            return
            
        # Tạo danh sách tên các mùa vụ để đưa vào ô chọn
        danh_sach_ten_hien_thi_mua_vu = [
            f"Vụ {vi_tri + 1}: {vu_mua[0].strftime('%d/%m/%Y')} đến {vu_mua[1].strftime('%d/%m/%Y')}" 
            for vi_tri, vu_mua in enumerate(danh_sach_cac_mua_vu)
        ]
        
        vi_tri_vu_duoc_chon = st.selectbox("🌾 3. Chọn Mùa Vụ Để Phân Tích Chi Tiết", range(len(danh_sach_cac_mua_vu)), format_func=lambda x: danh_sach_ten_hien_thi_mua_vu[x])
        vu_mua_dang_xet = danh_sach_cac_mua_vu[vi_tri_vu_duoc_chon]
        
        # Lọc ra những ngày nằm gọn trong mùa vụ đã chọn
        cac_ngay_trong_vu_mua_nay = sorted([
            ngay for ngay in so_cai_du_lieu_hoan_chinh.keys() 
            if vu_mua_dang_xet[0] <= datetime.strptime(ngay, "%Y-%m-%d").date() <= vu_mua_dang_xet[1]
        ])
        
        # BƯỚC 3: Cắt Giai Đoạn
        danh_sach_cac_giai_doan_cua_vu = chia_nho_mua_vu_thanh_cac_giai_doan(
            cac_ngay_trong_vu_mua_nay, 
            so_cai_du_lieu_hoan_chinh, 
            ten_bien_chi_so_goc, 
            sai_so_cat_giai_doan
        )
        
        st.success(f"✅ Hệ thống đang phân tích theo **{ten_chi_so_hien_thi}**. Đã cắt được thành công **{len(danh_sach_cac_giai_doan_cua_vu)} giai đoạn**.")

        # BƯỚC 4: Hiển thị kết quả (Biểu đồ & Bảng)
        st.subheader("📈 Biểu Đồ Phân Tích (Các đường kẻ dọc màu đỏ là mốc chia giai đoạn)")
        st.pyplot(ve_bieu_do_tong_quan_cac_chi_so(so_cai_du_lieu_hoan_chinh, danh_sach_cac_giai_doan_cua_vu))
        
        st.subheader("📋 Bảng Tổng Hợp Dữ Liệu Từng Ngày")
        du_lieu_hien_thi_len_bang = []
        for chi_muc_giai_doan, giai_doan in enumerate(danh_sach_cac_giai_doan_cua_vu):
            for ngay in giai_doan:
                du_lieu_hien_thi_len_bang.append({
                    "Giai đoạn": f"Giai đoạn {chi_muc_giai_doan + 1}",
                    "Ngày": ngay,
                    "Số Lần Tưới": so_cai_du_lieu_hoan_chinh[ngay]['so_lan_tuoi'],
                    "Thời Gian (Phút)": so_cai_du_lieu_hoan_chinh[ngay]['thoi_gian_tuoi_phut'],
                    "EC Trung Bình (TBEC)": so_cai_du_lieu_hoan_chinh[ngay]['tbec'],
                    "EC Yêu Cầu": so_cai_du_lieu_hoan_chinh[ngay]['ec_yeu_cau']
                })
        
        # Hiển thị bảng dữ liệu (dataframe) tràn viền
        st.dataframe(du_lieu_hien_thi_len_bang, use_container_width=True)
    else:
        st.info("👈 Bạn vui lòng tải lên cả 2 tệp Nhỏ Giọt và Châm Phân ở cột điều khiển bên trái để bắt đầu nhé.")

# Kích hoạt chạy chương trình
if __name__ == "__main__":
    main()
