# AutoSeller - 세션 기록 (Session 7)

날짜: 2026-05-20

---

## Step 7 꾹페이 자동결제 완성 (`uploader/domeggook_order.py`)

### 사업자지출증빙 입력 버그 수정

**문제**: `cashReceiptNum`은 hidden 필드. cashReceiptType='2' 선택 시 `cashReceiptComType` div가 표시되며 그 안에 4개 text input 존재:
- [0] `id='cashReceiptComTypeTitle'`, disabled=True → 레이블
- [1~3] 실제 입력 3개 (no id, not disabled)

**원인**: 전체 사업자번호(10자리)를 4개 필드 모두에 설정 → 검증 실패  
**해결**: 3분할 방식으로 각 입력에 설정
```python
b1, b2, b3 = biz_no_clean[:3], biz_no_clean[3:5], biz_no_clean[5:]
# native value setter + input/change/blur 이벤트
```

### 디버깅 과정에서 확인한 구조

- `showTaxInvoicePublicArea()` 함수는 value='3' (세금계산서)만 처리 → 사업자용(value='2')는 별도 처리
- `cashReceiptComType` div: `display:block`으로 value='2' 선택 시 표시
- `cashReceiptIndType` div: 개인소득공제용, `display:none`
- value='1'=개인소득공제, value='2'=사업자지출증빙, value='4'=미신청

### 최종 검증 결과

```
[domeggook_order] 결제 후 현재 URL: .../my_orderSuccess.php?orderUid=...&ordered=12500
[domeggook_order] 완료: ORDER_OK
[step7] 완료: 조회=1, 주문=1, 송장등록=0
```

DB: `ordered / ORDER_OK` 확인  
이머니 12,500원 결제 완료 (실제 꾹페이 차감)
