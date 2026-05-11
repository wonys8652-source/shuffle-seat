import dash
from dash import dcc, html, Input, Output, State, ALL, ctx
from dash.exceptions import PreventUpdate
import dash_bootstrap_components as dbc
import pandas as pd
import random
import io
import base64
import time

# 앱 초기화
app = dash.Dash(__name__, 
                external_stylesheets=[dbc.themes.FLATLY], 
                suppress_callback_exceptions=True)
server = app.server
app.index_string = '''
<!DOCTYPE html>
<html>
    <head>
        {%metas%}
        <title>{%title%}</title>
        {%favicon%}
        {%css%}
        <style>
            /* 1. 드롭다운 전체 높이 100px로 강제 고정 */
            #no-cluster-select .Select-control {
                min-height: 100px !important;
                display: flex !important;
                align-items: flex-start !important;
                padding-top: 5px !important;
                background-color: #2b3035 !important; /* 다크모드 배경색 */
            }

            /* 2. 선택된 학생 이름표(태그) 디자인: 하늘색 배경 + 검정 글씨 */
            [data-bs-theme='dark'] #no-cluster-select .Select-value {
                background-color: #90caf9 !important; /* 밝은 하늘색 */
                border: 1px solid #42a5f5 !important;
                border-radius: 4px !important;
                margin: 4px !important;
                padding: 2px !important;
            }

            /* 3. 이름표 안의 텍스트 색상 강제 지정 */
            [data-bs-theme='dark'] #no-cluster-select .Select-value-label {
                color: #000000 !important; /* 검정색 글자 (가독성 최고) */
                font-weight: bold !important;
                padding: 0 5px !important;
            }

            /* 4. 이름표 옆의 'x' 삭제 버튼 색상 */
            [data-bs-theme='dark'] #no-cluster-select .Select-value-icon {
                color: #000000 !important;
                border-right: 1px solid rgba(0,0,0,0.1) !important;
            }
            
            #no-cluster-select .Select-placeholder {
                line-height: 35px !important; /* 플레이스홀더 위치 조정 */
            }
            
            /* 학생 번호 입력 필드에서 화살표 제거 */
            input[type="number"]::-webkit-outer-spin-button,
            input[type="number"]::-webkit-inner-spin-button {
                -webkit-appearance: none;
                margin: 0;
            }
            input[type="number"] {
                -moz-appearance: textfield;
            }
            
            /* 분단별 박스에 배경색 추가 */
            .group-wrap {
                background-color: #F5F5F5;
                border: 2px solid #D0D0D0;
                border-radius: 8px;
                padding: 12px;
                margin: 10px 0;
            }
            [data-bs-theme='dark'] .group-wrap {
                background-color: #2A2B2D;
                border-color: #3E4042;
            }
        </style>
    </head>
    <body>
        {%app_entry%}
        <footer>
            {%config%}
            {%scripts%}
            {%renderer%}
        </footer>
    </body>
</html>
'''

# --- 1. 앱 레이아웃 ---
# 다크모드 적용을 위해 전체를 html.Div로 한 번 감싸줍니다.
app.layout = html.Div([
    html.Div(id="blank-output", style={"display": "none"}), # 다크모드 트리거용 빈 공간
    html.Div(id="print-trigger-dummy", style={"display": "none"}), # 인쇄 트리거용 빈 공간
    
    dbc.Container([
        # [수정 1] 상단바: 사이드바 영역(60px)을 피해 타이틀 시작
        dbc.Row([
            dbc.Col([
                html.Div([
                    html.H4("학급 자리 배치", id="main-title", className="my-0 fw-bold", 
                            style={"transition": "margin-left 0.25s ease-in-out", "marginLeft": "320px", "color": "var(--text-color)"}),
                    
                    dbc.Button("🔀 자리 배치 실행", id="generate-btn", color="primary", className="ms-4 me-2 fw-bold shadow-sm"),
                    dbc.Button("🔢 번호순 배치", id="assign-number-btn", color="info", outline=True, className="me-2"),
                    dbc.Button("🔄 배치 초기화", id="reset-btn", color="secondary", outline=True, className="fw-bold"),
                    dbc.Button("🖨️ 인쇄", id="print-btn", color="success", outline=True, className="fw-bold ms-2 shadow-sm"),
                ], className="d-flex align-items-center p-3")
            ], width=9),

            dbc.Col([
                html.Div([
                    html.Span("☀️ 라이트", className="me-2 fw-bold", style={"fontSize": "0.9rem"}),
                    dbc.Switch(id="theme-switch", value=False, className="d-inline-block", persistence=True),
                    html.Span("🌙 다크", className="ms-2 fw-bold", style={"fontSize": "0.9rem"}),
                ], className="d-flex align-items-center justify-content-end p-3")
            ], width=3)
        ], 
        className="g-0 shadow-sm", 
        style={
            "zIndex": 1000, 
            "position": "relative",
            "backgroundColor": "var(--bar-bg)",               # 💡 제미나이 톤 배경 변수
            "borderBottom": "1px solid var(--border-color)",  # 💡 테두리 색상 변수
            "transition": "background-color 0.4s ease"
        }),

        # [수정 2] 제미나이 스타일 사이드바 (화면 상하 꽉 채움, 고정형)
        html.Div([
            dbc.Button("☰", id="toggle-sidebar-btn", color="link", 
                       title="메뉴 접기",
                       style={
                           "position": "absolute", "left": "15px", "top": "15px", 
                           "fontSize": "1.8rem", "color": "var(--text-color)", "textDecoration": "none", "zIndex": 1011,
                           "borderRadius": "50%", "width": "50px", "height": "50px", "display": "flex", "alignItems": "center", "justifyContent": "center"
                       }, className="p-0 border-0"),

            # 🟢 환경설정 내용물
            html.Div([
                    html.H5("⚙️ 환경 설정", className="fw-bold mb-4", style={"color": "var(--text-color)", "marginTop": "10px"}),
                # 🟢 환경설정 내용물 버튼들 className 수정
                html.Div([
                    dbc.Button("🗂️ 분단 개수 설정", id="open-group-mgr-btn", 
                               className="btn w-100 mb-2 shadow-sm sidebar-btn", # 💡 sidebar-btn 추가!
                               style={"backgroundColor": "var(--btn-bg)", "color": "var(--btn-text)", "border": "1px solid var(--btn-border)", "textAlign": "left", "padding": "12px 15px", "borderRadius": "8px"}),
                    
                    dbc.Button("👥 학생 명단 관리", id="open-student-mgr-btn", 
                               className="btn w-100 mb-2 shadow-sm sidebar-btn", # 💡 sidebar-btn 추가!
                               style={"backgroundColor": "var(--btn-bg)", "color": "var(--btn-text)", "border": "1px solid var(--btn-border)", "textAlign": "left", "padding": "12px 15px", "borderRadius": "8px"}),
                    
                    dbc.Button("👫 짝꿍 배치 규칙", id="open-strategy-btn", 
                               className="btn w-100 mb-2 shadow-sm sidebar-btn", # 💡 sidebar-btn 추가!
                               style={"backgroundColor": "var(--btn-bg)", "color": "var(--btn-text)", "border": "1px solid var(--btn-border)", "textAlign": "left", "padding": "12px 15px", "borderRadius": "8px"}),
                    
                    dbc.Button("✅ 허용석/금지석 관리", id="open-fixed-mgr-btn", 
                               className="btn w-100 mb-2 shadow-sm sidebar-btn", # 💡 sidebar-btn 추가!
                               style={"backgroundColor": "var(--btn-bg)", "color": "var(--btn-text)", "border": "1px solid var(--btn-border)", "textAlign": "left", "padding": "12px 15px", "borderRadius": "8px"}),
                    
                    dbc.Button("⛔ 규칙 설정 (기피)", id="open-rules-mgr-btn", 
                               className="btn w-100 mb-2 shadow-sm sidebar-btn",      # 💡 sidebar-btn 추가!
                               style={"backgroundColor": "var(--btn-bg)", "color": "var(--btn-text)", "border": "1px solid var(--btn-border)", "textAlign": "left", "padding": "12px 15px", "borderRadius": "8px"}),        
                    
                    dbc.Button("💾 배치 결과 관리", id="open-seating-result-btn", 
                               className="btn w-100 mb-2 shadow-sm sidebar-btn",
                               style={"backgroundColor": "var(--btn-bg)", "color": "var(--btn-text)", "border": "1px solid var(--btn-border)", "textAlign": "left", "padding": "12px 15px", "borderRadius": "8px"}),
                ]),
                
                html.Div(id="alert-container", className="mt-3"),
                dbc.Alert("💡 책상을 클릭하여 고정석을 설정하세요.", color="secondary", className="mt-4 border-0", style={"fontSize": "0.85rem", "backgroundColor": "transparent", "color": "var(--text-color)"})
            ], 
            id="sidebar-content",
            style={
                "width": "300px", "padding": "20px", "marginTop": "80px",
                "opacity": "1", "visibility": "visible", 
                "transition": "opacity 0.2s ease-in-out" 
            }),

        ], id="sidebar",
        style={
            "position": "fixed", "top": "0px", "bottom": "0px", "left": "0px", 
            "width": "300px", 
            "zIndex": 1010,         
            "backgroundColor": "var(--bar-bg)",               # 💡 기존 #f8f9fa 지우고 변수로 교체!
            "borderRight": "1px solid var(--border-color)",   # 💡 테두리 색상 변수화
            "boxShadow": "4px 0px 15px rgba(0,0,0,0.05)", 
            "transition": "width 0.5s cubic-bezier(0.25, 0.8, 0.25, 1), background-color 0.4s ease", # 색상 변환 애니메이션 추가
            "overflowX": "hidden", "overflowY": "auto"
        }),

        # [수정 3] 오른쪽 메인 화면: 사이드바와 연동되도록 ID와 스타일 확인
        dbc.Row([
            dbc.Col([
                dbc.Card([
                    dbc.CardHeader(
                        html.Div([
                            html.Span("교실 자리 배치 레이아웃"),
                            html.Span(id="student-stats-display", className="ms-2 fw-normal text-muted", style={"fontSize": "0.9rem"})
                        ], className="d-flex align-items-center"), 
                        className="fw-bold"
                    ),
                    dbc.CardBody(id="main-layout-preview", style={"minHeight": "600px"})
                ])
            ], 
            id="main-col", # 💡 콜백에서 제어하기 위한 ID
            style={
                "flex": "1", 
                "transition": "margin-left 0.4s cubic-bezier(0.25, 0.8, 0.25, 1)", # 💡 사이드바와 동일한 애니메이션 속도
                "marginLeft": "320px", # 💡 초기값 (사이드바가 열린 상태)
                "padding": "20px"
            })
        ], className="mt-3 g-0"),

    
    # [팝업 1~4: 분단/전략/세부/명단 모달]
    dbc.Modal([
        dbc.ModalHeader(dbc.ModalTitle("분단 개수 설정")),
        dbc.ModalBody([
            dbc.Label("설정할 분단 개수를 선택하세요."),
            dbc.Row([
                dbc.Col(html.Div(f"{i}분단", id={'type': 'group-select-box', 'index': i},
                                className="text-center border rounded p-3 mb-2", style={"cursor": "pointer"})
                        , width=4) for i in range(1, 7)
            ], className="g-2")
        ]),
        dbc.ModalFooter([dbc.Button("저장 및 닫기", id="group-mgr-close-btn", color="success", className="w-100")]),
    ], id="group-mgr-modal", is_open=False, backdrop="static", style={"zIndex": 2000}),

    dbc.Modal([
        dbc.ModalHeader(dbc.ModalTitle("배치 전략 설정")),
        dbc.ModalBody([
            dbc.Label("짝꿍 배치 규칙을 선택하세요:"),
            dbc.RadioItems(
                options=[
                    {"label": "상관 없음 (전체 랜덤)", "value": "random"},
                    {"label": "동성끼리 우선 배치 (남남/여여)", "value": "same"},
                    {"label": "이성끼리 우선 배치 (남여)", "value": "diff"},
                ],
                value="random", id="placement-strategy", className="mt-2",
            ),
        ]),
        dbc.ModalFooter([dbc.Button("저장 및 닫기", id="strategy-close-btn", color="success")]),
    ], id="strategy-modal", is_open=False),

    dbc.Modal([
        dbc.ModalHeader(dbc.ModalTitle(id="modal-title")),
        dbc.ModalBody([
            dbc.Row([
                dbc.Col([
                    dbc.Label("행(세로)"),
                    dbc.InputGroup([
                        dbc.Button("-", id='modal-row-step-minus', color="secondary", outline=True),
                        dbc.Input(id='modal-row-step-val', value=5, type="number", className="text-center", readonly=True),
                        dbc.Button("+", id='modal-row-step-plus', color="secondary", outline=True),
                    ], size="sm")
                ], width=6),
                dbc.Col([
                    dbc.Label("열(가로)"),
                    dbc.InputGroup([
                        dbc.Button("-", id='modal-col-step-minus', color="secondary", outline=True),
                        dbc.Input(id='modal-col-step-val', value=2, type="number", className="text-center", readonly=True),
                        dbc.Button("+", id='modal-col-step-plus', color="secondary", outline=True),
                    ], size="sm")
                ], width=6),
            ], className="mb-4"),
            html.Hr(),
            html.Div([
                html.H6("혼자 앉는 자리 설정", className="fw-bold mb-1"),
                html.P("클릭하면 빈 자리(짝 없음)로 설정됩니다.", className="text-muted small mb-3"),
            ]),
            html.Div(id="modal-exclude-grid")
        ]),
        dbc.ModalFooter([dbc.Button("저장 및 닫기", id="modal-save-btn", color="success", className="w-100")]),
    ], id="edit-modal", is_open=False),

# [팝업] 학생 명단 관리 모달
    dbc.Modal([
        dbc.ModalHeader(dbc.ModalTitle("학생 명단 관리")),
        dbc.ModalBody([
            # 💡 수정된 부분: 수동 추가 박스와 엑셀 업로드 박스를 가로로 나란히 배치
            dbc.Row([
                # 왼쪽: 새 학생 수동 추가 박스 (너비 7/12)
                dbc.Col([
                    dbc.Card([
                        dbc.CardHeader("🧑‍🎓 새 학생 추가", className="fw-bold bg-light", style={"fontSize": "0.95rem"}),
                        dbc.CardBody([
                            dbc.Row([
                                dbc.Col(dbc.Input(id="new-student-no", type="number", placeholder="번호", size="sm", inputMode="numeric"), width=3),
                                dbc.Col(dbc.Input(id="new-student-name", type="text", placeholder="이름", size="sm"), width=4),
                                dbc.Col(dbc.Select(id="new-student-gender", options=[{"label": "남", "value": "남"}, {"label": "여", "value": "여"}], placeholder="성별", size="sm"), width=3),
                                dbc.Col(dbc.Button("추가", id="add-student-btn", color="primary", size="sm", className="w-100"), width=2),
                            ], className="g-2")
                        ], className="p-3")
                    ], className="shadow-sm h-100")
                ], width=7),
                
                # 오른쪽: 엑셀 파일 일괄 등록 박스 (너비 5/12)
                dbc.Col([
                    dbc.Card([
                        dbc.CardHeader("📁 엑셀 파일 관리", className="fw-bold bg-light", style={"fontSize": "0.95rem"}),
                        dbc.CardBody([
                            dbc.Row([
                                dbc.Col([
                                    dcc.Upload(
                                        id='upload-data', 
                                        children=dbc.Button("엑셀 파일로 일괄 등록", color="success", size="sm", className="w-100"),
                                        style={"width": "100%"}
                                    ),
                                    # 💡 [수정] 텍스트 컬러를 다크모드 대응 변수로 변경하고 마진 조정
                                    html.Div(id="upload-filename-display", 
                                            className="text-start mt-2 fw-bold", 
                                            style={"fontSize": "0.85rem", "color": "var(--text-color)", "wordBreak": "break-all"})
                                ], width=6),
                                dbc.Col(
                                    dbc.Button("양식 다운로드", id="btn-download", color="secondary", outline=True, size="sm", className="w-100"), width=6
                                ),
                            ], className="g-2")
                        ], className="p-3 d-flex flex-column justify-content-center h-100")
                    ], className="shadow-sm h-100")
                ], width=5)
            ], className="mb-4 align-items-stretch"), # 양쪽 박스의 높이를 똑같이 맞춤
            
            # 아래쪽: 기존 학생 목록 테이블 영역
            dbc.Row([
                dbc.Col([html.H6(id="count-male", style={"color": "#63B3ED", "fontWeight": "bold"}), html.Div(id="table-male-container")], width=6),
                dbc.Col([html.H6(id="count-female", style={"color": "#F687B3", "fontWeight": "bold"}), html.Div(id="table-female-container")], width=6),
            ]),
        ]),
        dbc.ModalFooter([dbc.Button("저장 및 닫기", id="student-mgr-close-btn", color="success")]),
    ], id="student-mgr-modal", is_open=False, size="xl"),
    
    # [팝업 5] 고정석 관리 모달 (버튼 위치 및 크기 수정)
    dbc.Modal([
        dbc.ModalHeader(dbc.ModalTitle("고정석 및 기피석 메뉴 관리")),
        dbc.ModalBody([
            dbc.Row([
                dbc.Col([
                    html.Label("1. 학생 선택", className="fw-bold"),
                    dbc.Select(id="fixed-student-select", placeholder="학생을 선택하세요..."),
                ], width=5),
                dbc.Col([
                    html.Label("2. 설정 모드 선택", className="fw-bold"),
                    dbc.RadioItems(
                        id='fixed-mode-selector',
                        options=[
                            {"label": "✅ 허용석 (이 자리들만 가능)", "value": "allow"},
                            {"label": "❌ 금지석 (이 자리들은 제외)", "value": "deny"},
                        ],
                        value="allow",
                        inline=True,
                        className="mt-1"
                    ),
                ], width=7),
            ], className="mb-3 p-3 border rounded", style={"backgroundColor": "var(--card-bg)"}), # 💡 bg-light 대신 변수 사용
            html.Div(id="fixed-rules-table"),
            html.Hr(),
            # 💡 수정된 부분: 텍스트와 버튼을 한 줄(Row)에 배치하고 버튼 크기를 줄였습니다.
            dbc.Row([
                dbc.Col(html.H6("아래 교실 모형에서 좌석을 클릭하여 추가하세요", className="fw-bold m-0"), width=8, className="d-flex align-items-center"),
                dbc.Col(dbc.Button("현재 선택된 좌석 저장", id="add-fixed-rule-btn", color="primary", size="sm", className="w-100"), width=4)
            ], className="mb-3"),
            html.Div(id="fixed-layout-preview", className="bg-light p-3 rounded border")
        ]),
        dbc.ModalFooter([dbc.Button("저장 및 닫기", id="fixed-mgr-close-btn", color="success")]),
    ], id="fixed-mgr-modal", is_open=False, size="xl"),

# [팝업 6] 메인 화면의 개별 좌석 클릭 모달
dbc.Modal([
    dbc.ModalHeader(dbc.ModalTitle(id="seat-modal-title"), className="fw-bold"),
    dbc.ModalBody([
        dbc.Label("📌 이 자리에 앉힐 학생 지정 (고정석)", className="fw-bold"),
        dbc.Select(id="seat-student-select", placeholder="학생을 선택하세요...", className="mb-3"),
        
        html.Hr(),
        
        dbc.Label("🚻 이 자리 성별 조건 (클릭 시 자동 저장)", className="fw-bold"),
        
        # 💡 지저분했던 style 코드를 지우고, outline=True 속성을 넣어 테두리 버튼으로 깔끔하게 바꿨습니다!
        html.Div([
            dbc.Button("⚪ 무관", id="btn-gender-any", color="secondary", outline=True, className="fw-bold flex-grow-1 shadow-sm"),
            dbc.Button("🔵 남학생", id="btn-gender-m", color="info", outline=True, className="fw-bold flex-grow-1 shadow-sm"),
            dbc.Button("🔴 여학생", id="btn-gender-f", color="danger", outline=True, className="fw-bold flex-grow-1 shadow-sm"),
        ], className="w-100 mb-3 d-flex gap-3"),
        
        html.Hr(),

        dbc.Checkbox(
            id="seat-exclude-check", 
            label="🚫 이 자리를 빈 자리(통로)로 설정", 
            value=False,
            inputClassName="btn-check", 
            labelClassName="btn btn-outline-danger w-100 fw-bold" 
        )
    ]),
    dbc.ModalFooter([
        dbc.Button("저장 및 닫기", id="close-seat-modal-btn", color="success", className="shadow-sm"),
    ])
], id="seat-setting-modal", is_open=False, centered=True),

    # [팝업 7] 규칙 설정 (학생 간 기피/밀집 방지) 모달
dbc.Modal([
    dbc.ModalHeader(dbc.ModalTitle("특수 규칙 설정 (학생 간 관계 제어)")),
    dbc.ModalBody([
        dbc.Tabs([
            dbc.Tab([
                html.Div([
                    html.H6("📌 특정 두 학생 짝꿍 방지", className="fw-bold mt-3 mb-1"),
                    html.P("선택한 두 학생은 서로 바로 옆자리(짝꿍)가 될 수 없습니다.", className="text-muted small"),
                    dbc.Row([
                        # 💡 dcc.Dropdown 대신 dbc.Select로 변경하여 다른 메뉴와 형식을 맞춥니다.
                        dbc.Col(dbc.Select(id='no-pair-1', placeholder="학생 A 선택"), width=5),
                        dbc.Col(dbc.Select(id='no-pair-2', placeholder="학생 B 선택"), width=5),
                        dbc.Col(dbc.Button("추가", id='add-no-pair-btn', color="primary", className="w-100"), width=2)
                    ], className="mb-3"),
                    html.Div(id='no-pair-list')
                    # 💡 [중요] className에서 bg-light를 제거하고 다크모드 변수(--input-bg)를 적용합니다.
                ], className="p-3 border rounded mt-2", style={"backgroundColor": "var(--input-bg)"})
            ], label="짝꿍 방지 규칙"),
            
           dbc.Tab([
                html.Div([
                    html.H6("📌 특정 학생 그룹 밀집(3x3) 방지", className="fw-bold mt-3 mb-1"),
                    html.P("그룹으로 묶인 학생들은 상하좌우와 대각선 방향으로 3x3 범위 내에 붙어 앉을 수 없습니다.", className="text-muted small"),
                    
                    # 💡 1. 추가된 규칙 리스트를 위로 올림
                    html.Div(id='no-cluster-list', className="mt-2 mb-3"), 

                    html.Hr(), # 구분선 추가

                    html.P("아래 명단에서 학생들을 선택하고 '그룹 규칙 추가'를 누르세요.", className="text-muted small mb-2"),
                    
                    # 💡 2. 학생 선택 그리드
                    html.Div(id='cluster-selection-grid', className="mb-3 p-3 border rounded",
                            style={
                                "display": "grid", 
                                "gridTemplateColumns": "repeat(auto-fill, minmax(100px, 1fr))", 
                                "gap": "10px", 
                                "maxHeight": "250px", 
                                "overflowY": "auto",
                                "backgroundColor": "var(--input-bg)",
                                "userSelect": "none",
                                "WebkitUserSelect": "none",
                                "MozUserSelect": "none",
                                "msUserSelect": "none",
                                "pointerEvents": "none"  # 그리드 자체는 클릭 불가능
                            }),
                    
                    dbc.Row([
                        dbc.Col(dbc.Button("선택 초기화", id='clear-cluster-temp-btn', color="secondary", outline=True, size="sm"), width=4),
                        dbc.Col(dbc.Button("그룹 규칙 추가", id='add-no-cluster-btn', color="primary", className="w-100"), width=8)
                    ]),
                    
                ], className="p-3 border rounded mt-2", style={"backgroundColor": "var(--input-bg)"})
            ], label="밀집 방지 규칙"),
        ])
    ]),
    dbc.ModalFooter([dbc.Button("저장 및 닫기", id="rules-mgr-close-btn", color="success")]),
], id="rules-mgr-modal", is_open=False, size="lg"),
    

    # 상태 관리를 위한 Stores
    # storage_type='local'을 사용하면 브라우저 캐시에 저장되어 새로고침/재접속 후에도 데이터 유지
    dcc.Store(id='stored-data', data=[], storage_type='local'),  # 학생명단 (영구 저장)
    dcc.Store(id='edit-row-idx', data=None), 
    dcc.Store(id='groups-config', data=[{"id": i, "rows": 5, "cols": 2, "seats": {}, "exclude": []} for i in range(1, 4)], storage_type='local'),  # 조 설정 (영구 저장)
    dcc.Store(id='editing-group-id'),
    dcc.Store(id='selected-group-count', data=3),
    dcc.Store(id='fixed-seats-config', data=[], storage_type='local'),  # 고정석 설정 (영구 저장)
    dcc.Store(id='temp-fixed-seats', data=[]),
    dcc.Store(id='assigned-map-store', data={}),
    dcc.Store(id="current-edit-seat", data=None),
    dcc.Store(id='special-rules-store', data={'no_pair': [], 'no_cluster': []}, storage_type='local'),  # 특별 규칙 (영구 저장)
    dcc.Store(id='temp-cluster-selection', data=[]),
    dcc.Store(id='print-html-store', data=""),
    dcc.Store(id='seating-results-store', data=[], storage_type='local'),  # 저장된 자리 배치 결과 (영구 저장)
    dcc.Store(id='current-seating-result', data=None),  # 현재 배치 결과
    dcc.Download(id="download-template"),
    dcc.Download(id="download-seating-backup"),

# [팝업 7-1] 자리 배치 결과 저장 모달
dbc.Modal([
    dbc.ModalHeader(dbc.ModalTitle("💾 자리 배치 결과 저장")),
    dbc.ModalBody([
        html.P("현재 배치 결과를 저장하시겠습니까?", className="mb-3"),
        dbc.Label("저장 이름 (선택사항):", className="fw-bold mb-2"),
        dbc.Input(id="seating-save-name", placeholder="예: 2024년 5월 배치", type="text", className="mb-3"),
        html.Hr(),
        html.Div([
            html.P("💡 저장된 배치 목록:", className="fw-bold mb-2"),
            html.Div(id="seating-results-list", style={"maxHeight": "200px", "overflowY": "auto", "border": "1px solid #ddd", "borderRadius": "5px", "padding": "10px"})
        ], className="mb-3"),
    ]),
    dbc.ModalFooter([
        dbc.Button("저장하기", id="save-seating-result-btn", color="success", className="me-2"),
        dbc.Button("다운로드 백업", id="backup-seating-btn", color="info", className="me-2"),
        dbc.Button("취소", id="cancel-save-seating-btn", color="secondary"),
    ]),
], id="seating-save-modal", is_open=False, backdrop="static"),

# [팝업 8] 인쇄 설정 모달
dbc.Modal([
    dbc.ModalHeader(dbc.ModalTitle("🖨️ 인쇄 설정")),
    dbc.ModalBody([
        dbc.Label("📐 인쇄 방향 선택", className="fw-bold mb-2"),
        dbc.RadioItems(
            id="print-orientation",
            options=[
                {"label": "교사 기준 (칠판이 아래쪽)", "value": "teacher"},
                {"label": "학생 기준 (칠판이 위쪽)", "value": "student"},
            ],
            value="teacher",
            className="mb-4",
        ),
        html.Hr(),
        dbc.Label("📋 추가 옵션", className="fw-bold mb-2"),
        dbc.Checklist(
            id="print-options",
            options=[
                {"label": "오른쪽에 학생 명렬표 포함 (번호, 이름 순)", "value": "roster"},
            ],
            value=[],
            className="mb-3",
        ),
    ]),
    dbc.ModalFooter([
        dbc.Button("취소", id="print-modal-close-btn", color="secondary", outline=True, className="me-2"),
        dbc.Button("🖨️ 인쇄하기", id="do-print-btn", color="success", className="fw-bold"),
    ]),
], id="print-modal", is_open=False, centered=True, style={"zIndex": 2000}),


], fluid=True)
], id="main-wrapper")



# --- 2. 환경설정 콜백부 ---

@app.callback(
    [Output('student-mgr-modal', 'is_open'),
     Output('group-mgr-modal', 'is_open'),
     Output('strategy-modal', 'is_open'),
     Output('edit-modal', 'is_open'),
     Output('fixed-mgr-modal', 'is_open'),
     Output('editing-group-id', 'data'),
     Output('modal-title', 'children'),
     Output('modal-row-step-val', 'value'),
     Output('modal-col-step-val', 'value')],
    [Input('open-student-mgr-btn', 'n_clicks'),
     Input('student-mgr-close-btn', 'n_clicks'),
     Input('open-group-mgr-btn', 'n_clicks'),
     Input('group-mgr-close-btn', 'n_clicks'),
     Input('open-strategy-btn', 'n_clicks'),
     Input('strategy-close-btn', 'n_clicks'),
     Input('open-fixed-mgr-btn', 'n_clicks'),
     Input('fixed-mgr-close-btn', 'n_clicks'),
     Input({'type': 'open-edit', 'index': ALL}, 'n_clicks'),
     Input('modal-save-btn', 'n_clicks')],
    [State('groups-config', 'data')],
    prevent_initial_call=True
)
def handle_modals(s_on, s_off, g_on, g_off, st_on, st_off, f_on, f_off, edit_clicks, m_save, config):
    tid = ctx.triggered_id
    if not tid: raise PreventUpdate
    res = [False, False, False, False, False, dash.no_update, dash.no_update, dash.no_update, dash.no_update]

    if tid == 'open-student-mgr-btn': res[0] = True
    elif tid == 'student-mgr-close-btn': res[0] = False
    elif tid == 'open-group-mgr-btn': res[1] = True
    elif tid == 'group-mgr-close-btn': res[1] = False
    elif tid == 'open-strategy-btn': res[2] = True
    elif tid == 'strategy-close-btn': res[2] = False
    elif tid == 'open-fixed-mgr-btn': res[4] = True
    elif tid == 'fixed-mgr-close-btn': res[4] = False
    elif isinstance(tid, dict) and tid.get('type') == 'open-edit':
        if not any(edit_clicks): raise PreventUpdate
        g_id = tid['index']
        g_data = next((g for g in config if g['id'] == g_id), {"rows": 5, "cols": 2})
        res[3], res[5], res[6], res[7], res[8] = True, g_id, f"{g_id}분단 세부 설정", g_data['rows'], g_data['cols']
    elif tid == 'modal-save-btn': res[3] = False
    return res

@app.callback(
    Output('groups-config', 'data'),
    Output('modal-exclude-grid', 'children'),
    Output('modal-row-step-val', 'value', allow_duplicate=True), 
    Output('modal-col-step-val', 'value', allow_duplicate=True), 
    Input('selected-group-count', 'data'),
    Input('modal-row-step-minus', 'n_clicks'),
    Input('modal-row-step-plus', 'n_clicks'),
    Input('modal-col-step-minus', 'n_clicks'),
    Input('modal-col-step-plus', 'n_clicks'),
    Input('modal-row-step-val', 'value'),
    Input('modal-col-step-val', 'value'),
    Input({'type': 'ex-seat-click', 'r': ALL, 'c': ALL}, 'n_clicks'),
    Input({'type': 'gender-btn', 'group': ALL, 'row': ALL, 'col': ALL, 'val': ALL}, 'n_clicks'),
    Input('reset-btn', 'n_clicks'), 
    State('groups-config', 'data'),
    State('editing-group-id', 'data'),
    prevent_initial_call=True
)
def sync_config(g_count, rm, rp, cm, cp, rv, cv, ex_clicks, gender_clicks, reset_btn, config, edit_id):
    tid = ctx.triggered_id
    
    if isinstance(tid, dict):
        trigger_val = ctx.triggered[0]['value']
        if not trigger_val: raise PreventUpdate

    if not tid or tid == 'selected-group-count':
        new_c = []
        for i in range(1, g_count + 1):
            existing = next((g for g in config if g['id'] == i), None)
            new_c.append(existing if existing else {"id": i, "rows": 5, "cols": 2, "seats": {}, "exclude": []})
        return new_c, dash.no_update, dash.no_update, dash.no_update

    if tid == 'reset-btn':
        for g in config: g['seats'] = {} 
        return config, dash.no_update, dash.no_update, dash.no_update

    if isinstance(tid, dict) and tid.get('type') == 'gender-btn':
        g_id, r, c, val = tid['group'], tid['row'], tid['col'], tid['val']
        for g in config:
            if g['id'] == g_id: g['seats'][f"{r}-{c}"] = val
        return config, dash.no_update, dash.no_update, dash.no_update

    target_idx = next((i for i, g in enumerate(config) if g['id'] == edit_id), None)
    if target_idx is None: return config, dash.no_update, dash.no_update, dash.no_update

    r, c = (rv if rv else 5), (cv if cv else 2)
    if tid == 'modal-row-step-minus': r = max(1, r - 1)
    elif tid == 'modal-row-step-plus': r += 1
    elif tid == 'modal-col-step-minus': c = max(1, c - 1)
    elif tid == 'modal-col-step-plus': c += 1
    config[target_idx]['rows'], config[target_idx]['cols'] = r, c

    if isinstance(tid, dict) and tid.get('type') == 'ex-seat-click':
        pos = f"{tid['r']}-{tid['c']}"
        if pos in config[target_idx]['exclude']: config[target_idx]['exclude'].remove(pos)
        else: config[target_idx]['exclude'].append(pos)

    grid = [dbc.Row([
        dbc.Col(html.Div(f"{ri+1}-{ci+1}", id={'type': 'ex-seat-click', 'r': ri, 'c': ci},
                         className=f"text-center border rounded p-2 {'bg-danger text-white' if f'{ri}-{ci}' in config[target_idx]['exclude'] else 'bg-body'}",
                         style={"cursor": "pointer"}), className="p-1") for ci in range(c)
    ], className="g-0 justify-content-center") for ri in range(r)]

    return config, grid, r, c

@app.callback(
    Output('stored-data', 'data'),
    Output('table-male-container', 'children'),
    Output('table-female-container', 'children'),
    Output('count-male', 'children'),
    Output('count-female', 'children'),
    Output('edit-row-idx', 'data'),
    Output('new-student-no', 'value'),
    Output('new-student-name', 'value'),
    Output('new-student-gender', 'value'),
    Output('upload-data', 'contents'), # 💡 1번 문제 해결: 업로드 데이터 초기화용 Output 추가
    Input('add-student-btn', 'n_clicks'),
    Input('upload-data', 'contents'),
    Input({'type': 'del-student', 'index': ALL}, 'n_clicks'),
    Input({'type': 'edit-btn', 'index': ALL}, 'n_clicks'),
    Input({'type': 'save-btn', 'index': ALL}, 'n_clicks'),
    State({'type': 'in-no', 'index': ALL}, 'value'),
    State({'type': 'in-name', 'index': ALL}, 'value'),
    State({'type': 'in-gender', 'index': ALL}, 'value'),
    State('new-student-no', 'value'),
    State('new-student-name', 'value'),
    State('new-student-gender', 'value'),
    State('stored-data', 'data'),
    State('edit-row-idx', 'data'),
    prevent_initial_call=True
)
def manage_students(add_n, upload, del_n, edit_n, save_n, in_nos, in_names, in_genders, n_no, n_na, n_ge, current_data, current_edit_idx):
    tid = ctx.triggered_id
    new_list = list(current_data) if current_data else []
    next_edit_idx = current_edit_idx
    
    # 데이터 추가/수정/삭제 로직
    if tid == 'add-student-btn' and n_no and n_na and n_ge:
        new_list.append({"번호": int(n_no), "이름": n_na, "성별": n_ge})
    elif tid == 'upload-data' and upload:
        try:
            df = pd.read_excel(io.BytesIO(base64.b64decode(upload.split(',')[1])))
            if all(col in df.columns for col in ['번호', '이름', '성별']):
                new_list = df.to_dict('records')
        except Exception: pass
    elif isinstance(tid, dict) and tid.get('type') == 'del-student':
        new_list.pop(tid['index'])
    elif isinstance(tid, dict) and tid.get('type') == 'edit-btn':
        next_edit_idx = tid['index'] if tid['index'] >= 0 else None
    elif isinstance(tid, dict) and tid.get('type') == 'save-btn':
        if in_nos and in_names and in_genders:
            new_list[tid['index']] = {"번호": int(in_nos[0]), "이름": in_names[0], "성별": in_genders[0]}
        next_edit_idx = None

    # 번호순 정렬
    new_list = sorted(new_list, key=lambda x: int(x.get('번호', 0)))
    
    # 💡 수정된 부분: 
    # 1. 수정/삭제 버튼을 링크형에서 외곽선 버튼(outline=True)으로 변경했습니다.
    # 2. html.Th(테이블 헤더)에 width 속성을 주어 열 너비가 고정되도록 했습니다.
    def create_table(gender):
        subset = [(i, s) for i, s in enumerate(new_list) if s['성별'] == gender]
        rows = []
        for idx, s in subset:
            if idx == next_edit_idx:
                # [수정 모드] 입력 폼 렌더링
                rows.append(html.Tr([
                    html.Td(dbc.Input(id={'type': 'in-no', 'index': idx}, value=s['번호'], type="number", size="sm")),
                    html.Td(dbc.Input(id={'type': 'in-name', 'index': idx}, value=s['이름'], size="sm")),
                    html.Td(dbc.Select(id={'type': 'in-gender', 'index': idx}, options=[{"label": "남", "value": "남"}, {"label": "여", "value": "여"}], value=s['성별'], size="sm")),
                    html.Td([
                        dbc.Button("저장", id={'type': 'save-btn', 'index': idx}, color="success", size="sm", className="me-1"),
                        dbc.Button("취소", id={'type': 'edit-btn', 'index': -1}, color="secondary", size="sm")
                    ], style={"whiteSpace": "nowrap", "textAlign": "center"})
                ]))
            else:
                # [일반 모드] 버튼형으로 렌더링
                rows.append(html.Tr([
                    html.Td(s['번호'], className="align-middle text-center"), 
                    html.Td(s['이름'], className="align-middle text-center"), 
                    html.Td(s['성별'], className="align-middle text-center"), 
                    html.Td([
                        dbc.Button("수정", id={'type': 'edit-btn', 'index': idx}, 
                                   color="info", outline=True, size="sm", className="me-1"),
                        dbc.Button("삭제", id={'type': 'del-student', 'index': idx}, 
                                   color="danger", outline=True, size="sm")
                    ], style={"whiteSpace": "nowrap", "textAlign": "center"})
                ]))
                
        # 헤더 너비(20%, 30%, 20%, 30%)를 고정하여 폼이 바뀌어도 표가 출렁이지 않음
        return dbc.Table([
            html.Thead(html.Tr([
                html.Th("번호", style={"width": "20%", "textAlign": "center"}), 
                html.Th("이름", style={"width": "30%", "textAlign": "center"}), 
                html.Th("성별", style={"width": "20%", "textAlign": "center"}), 
                html.Th("관리", style={"width": "30%", "textAlign": "center"})
            ])), 
            html.Tbody(rows)
        ], bordered=True, hover=True, size="sm", className="table-fixed")
        
    # 마지막 None 값은 upload-data의 contents를 초기화하여 같은 파일을 또 불러올 수 있게 합니다.
    return new_list, create_table("남"), create_table("여"), f"남학생 - {len([s for s in new_list if s['성별']=='남'])}명", f"여학생 - {len([s for s in new_list if s['성별']=='여'])}명", next_edit_idx, None, "", None, None

@app.callback(
    Output("download-template", "data"),
    Input("btn-download", "n_clicks"),
    State('stored-data', 'data'),
    prevent_initial_call=True
)
def download_template(n, students):
    """메모리에서 직접 엑셀 파일 생성 (Render.com 호환)"""
    if not students:
        # 빈 데이터일 경우 기본 양식 제공
        df = pd.DataFrame({
            "번호": [1, 2, 3],
            "이름": ["학생1", "학생2", "학생3"],
            "성별": ["남", "여", "남"]
        })
    else:
        # 실제 학생 데이터 사용
        df = pd.DataFrame(students)
    
    # BytesIO를 사용하여 메모리에 파일 생성 (디스크 쓰기 불필요)
    buffer = io.BytesIO()
    with pd.ExcelWriter(buffer, engine='openpyxl') as writer:
        df.to_excel(writer, sheet_name='학생명단', index=False)
    buffer.seek(0)
    
    # Dash의 send_bytes로 메모리에서 직접 반환 (Render.com 호환)
    return dcc.send_bytes(buffer.getvalue(), "학생명단.xlsx")

@app.callback(
    Output('selected-group-count', 'data'),
    Output({'type': 'group-select-box', 'index': ALL}, 'className'),
    Input({'type': 'group-select-box', 'index': ALL}, 'n_clicks'),
    State('selected-group-count', 'data'),
    prevent_initial_call=True
)
def update_group_count(n, current):
    new = ctx.triggered_id['index'] if ctx.triggered_id else current
    return new, ["text-center border rounded p-3 mb-2 " + ("bg-success text-white" if i == new else "bg-light") for i in range(1, 7)]


# --- 3. 고정석 메뉴 전용 콜백 (허용/금지 로직 적용) ---
@app.callback(
    Output('fixed-student-select', 'options'),
    Input('stored-data', 'data')
)
def update_fixed_dropdown(students):
    if not students: return []
    return [{"label": f"{s['번호']}번 {s['이름']} ({s['성별']})", "value": s['번호']} for s in students]

@app.callback(
    Output('temp-fixed-seats', 'data'),
    [Input({'type': 'fixed-seat-click', 'g': ALL, 'r': ALL, 'c': ALL}, 'n_clicks'),
     Input('fixed-student-select', 'value'),
     Input('fixed-mode-selector', 'value')],
    [State('temp-fixed-seats', 'data'),
     State('fixed-seats-config', 'data'),
     State('groups-config', 'data')],
    prevent_initial_call=True
)
def toggle_temp_fixed_seats(clicks, student_no, mode, temp_data, fixed_config, group_config):
    tid = ctx.triggered_id
    if not tid: raise PreventUpdate
    
    if isinstance(tid, str) and tid in ['fixed-student-select', 'fixed-mode-selector']:
        if not student_no: return []
        rule = next((r for r in fixed_config if r['no'] == int(student_no)), None)
        if not rule: return []
        return rule.get('allowed', []) if mode == 'allow' else rule.get('forbidden', [])
        
    if isinstance(tid, dict) and tid.get('type') == 'fixed-seat-click':
        g_id, r, c = tid['g'], tid['r'], tid['c']
        g_data = next((g for g in group_config if g['id'] == g_id), None)
        if g_data and f"{r}-{c}" in g_data['exclude']: 
            return dash.no_update
        seat_str = f"{g_id}-{r}-{c}"
        temp = list(temp_data) if temp_data else []
        if seat_str in temp: temp.remove(seat_str)
        else: temp.append(seat_str)
        return temp
    return dash.no_update

@app.callback(
    Output('fixed-layout-preview', 'children'),
    [Input('temp-fixed-seats', 'data'),
     Input('fixed-mode-selector', 'value'),
     Input('groups-config', 'data'),
     Input('fixed-mgr-modal', 'is_open')]
)
def render_fixed_preview(temp_seats, mode, config, is_open):
    if not is_open: raise PreventUpdate
    temp_seats = temp_seats or []
    
    # 허용석(allow)은 녹색, 금지석(deny)은 빨간색으로 표시
    active_bg = "bg-success text-white fw-bold shadow" if mode == 'allow' else "bg-danger text-white fw-bold shadow"
    
    layout = dbc.Row([
        dbc.Col([
            html.Div([
                html.B(f"{g['id']}분단", className="text-muted d-block text-center mb-1"),
                html.Div([
                    # 💡 [핵심 수정] 여기서 r 루프가 빠져있어서 NameError가 발생했던 것입니다.
                    dbc.Row([
                        dbc.Col(
                            html.Div(f"{r+1}-{c+1}", 
                                     id={'type': 'fixed-seat-click', 'g': g['id'], 'r': r, 'c': c}, 
                                     # 💡 [다크모드 수정] bg-white 대신 bg-body 혹은 투명 배경 적용
                                     className="text-center border p-2 mb-1 rounded " + 
                                               ("bg-dark text-white" if f"{r}-{c}" in g['exclude'] else 
                                               (active_bg if f"{g['id']}-{r}-{c}" in temp_seats else "bg-body")),
                                     style={"cursor": ("not-allowed" if f"{r}-{c}" in g['exclude'] else "pointer"), "fontSize": "0.8rem"}
                            ), width=True, className="p-1"
                        ) for c in range(g['cols'])
                    ], className="g-0") for r in range(g['rows']) # 💡 r 루프 추가 완료
                # 💡 [다크모드 수정] bg-white 제거 및 테마 배경색 적용
                ], className="border p-1 rounded", style={"backgroundColor": "var(--card-bg)"}) 
            ])
        ], width={"size": True}) for g in config
    ], className="g-3 justify-content-center")
    
    return layout # 💡 원래대로 layout만 바로 return 하도록 되돌려줍니다.

@app.callback(
    Output('fixed-seats-config', 'data'),
    Output('fixed-rules-table', 'children'),
    [Input('add-fixed-rule-btn', 'n_clicks'),
     Input({'type': 'del-fixed-rule', 'index': ALL}, 'n_clicks'),
     Input('fixed-mgr-modal', 'is_open')],
    [State('fixed-student-select', 'value'),
     State('fixed-mode-selector', 'value'),
     State('temp-fixed-seats', 'data'),
     State('fixed-seats-config', 'data'),
     State('stored-data', 'data')]
)
def manage_fixed_rules(add_n, del_clicks, is_open, std_no, mode, temp_seats, fixed_config, student_data):
    if not is_open: raise PreventUpdate
    tid = ctx.triggered_id
    fixed_config = fixed_config or []
    
    if tid == 'add-fixed-rule-btn' and std_no:
        std_no = int(std_no)
        std_name = next((s['이름'] for s in student_data if s['번호'] == std_no), "알수없음")
        rule = next((r for r in fixed_config if r['no'] == std_no), None)
        
        if not rule:
            rule = {"no": std_no, "name": std_name, "allowed": [], "forbidden": [], "direct": False}
            fixed_config.append(rule)
            
        if mode == "allow":
            rule['allowed'] = temp_seats or []
            rule['forbidden'] = [s for s in rule.get('forbidden', []) if s not in rule['allowed']]
        else:
            rule['forbidden'] = temp_seats or []
            rule['allowed'] = [s for s in rule.get('allowed', []) if s not in rule['forbidden']]
            
        rule['direct'] = False 
        
    elif isinstance(tid, dict) and tid.get('type') == 'del-fixed-rule':
        idx_to_del = tid['index']
        fixed_config = [r for r in fixed_config if r['no'] != idx_to_del]
        
    if not fixed_config:
        table = html.P("설정된 고정/기피석 규칙이 없습니다.", 
                       className="text-muted small text-center p-3 border rounded",
                       style={"backgroundColor": "var(--card-bg)", "color": "var(--text-color)"})
    else:
        rows = []
        for r in fixed_config:
            allowed_str = ", ".join([f"{s.split('-')[0]}분단 {int(s.split('-')[1])+1}-{int(s.split('-')[2])+1}" for s in r.get('allowed', [])])
            forbidden_str = ", ".join([f"{s.split('-')[0]}분단 {int(s.split('-')[1])+1}-{int(s.split('-')[2])+1}" for s in r.get('forbidden', [])])
            
            rules_display = []
            if allowed_str:
                # 💡 수정된 부분: 허용석 뱃지 컬러를 success(녹색)로 변경했습니다.
                rules_display.append(html.Div([dbc.Badge("허용석", color="success", className="me-2"), html.Span(allowed_str, style={'fontSize': '0.85rem'})]))
            if forbidden_str:
                rules_display.append(html.Div([dbc.Badge("금지석", color="danger", className="me-2"), html.Span(forbidden_str, style={'fontSize': '0.85rem'})], className="mt-1"))
            
            if not rules_display:
                continue
                
            rows.append(html.Tr([
                html.Td(f"{r['no']}번 {r['name']}", className="align-middle fw-bold"),
                html.Td(rules_display, className="align-middle"),
                html.Td(dbc.Button("삭제", id={'type': 'del-fixed-rule', 'index': r['no']}, size="sm", color="danger", outline=True), className="align-middle")
            ]))
            
        if rows:
            table = dbc.Table([
                html.Thead(html.Tr([html.Th("학생"), html.Th("규칙 내용"), html.Th("관리")])), 
                html.Tbody(rows)
            ], size="sm", bordered=True, className="mb-0", style={"backgroundColor": "var(--card-bg)"})
        else:
            table = html.P("설정된 고정/기피석 규칙이 없습니다.", 
                           className="text-muted small text-center p-3 border rounded",
                           style={"backgroundColor": "var(--card-bg)"})
    return fixed_config, table

# --- 4. 메인 화면 책상 클릭 시: 지정 좌석 모달 로직 (자동 저장 및 닫기 완벽 통합) ---
@app.callback(
    Output('seat-setting-modal', 'is_open'),
    Output('current-edit-seat', 'data'),
    Output('seat-modal-title', 'children'),
    Output('seat-student-select', 'options'),
    Output('seat-student-select', 'value'),
    Output('seat-exclude-check', 'value'),
    Output('groups-config', 'data', allow_duplicate=True),
    Output('fixed-seats-config', 'data', allow_duplicate=True),
    # 💡 [추가됨] 성별 버튼 3개의 색칠(outline) 상태를 제어하기 위한 Output
    Output('btn-gender-any', 'outline'),
    Output('btn-gender-m', 'outline'),
    Output('btn-gender-f', 'outline'),
    [Input({'type': 'seat-click', 'pos': ALL}, 'n_clicks'),
     Input('close-seat-modal-btn', 'n_clicks'),
     Input('seat-student-select', 'value'), 
     Input('seat-exclude-check', 'value'),
     Input('btn-gender-any', 'n_clicks'), 
     Input('btn-gender-m', 'n_clicks'),
     Input('btn-gender-f', 'n_clicks')], 
    [State('groups-config', 'data'),
     State('fixed-seats-config', 'data'),
     State('stored-data', 'data'),
     State('current-edit-seat', 'data'),
     State('seat-setting-modal', 'is_open')],
    prevent_initial_call=True
)
def handle_seat_modal(clicks, close_btn, student_val, exclude_val, g_any, g_m, g_f, config, fixed_config, student_data, current_seat, is_open):
    tid = ctx.triggered_id
    if not tid: raise PreventUpdate

    # 1. 좌석을 클릭해서 모달을 열 때
    if isinstance(tid, dict) and tid.get('type') == 'seat-click':
        if not any(clicks): raise PreventUpdate
        seat_id = tid['pos']
        g_id, r, c = seat_id.split('-')
        key_short = f"{r}-{c}"

        title = f"좌석 설정 ({g_id}분단 {int(r)+1}행 {int(c)+1}열)"
        options = [{"label": "지정 안 함", "value": ""}] + [{"label": f"{s['번호']}번 {s['이름']} ({s['성별']})", "value": s['번호']} for s in student_data]

        fixed_config = fixed_config or []
        existing_rule = next((rule for rule in fixed_config if seat_id in rule.get('allowed', [])), None)
        current_student = str(existing_rule['no']) if existing_rule else ""

        target_g = next((g for g in config if str(g['id']) == g_id), None)
        is_excluded = key_short in target_g['exclude'] if target_g else False
        
        # 💡 [추가] 저장된 성별 설정을 불러와서, 해당 버튼만 색칠되게(outline=False) 만듭니다.
        curr_gender = 'Any'
        if target_g and 'seats' in target_g:
            curr_gender = target_g['seats'].get(key_short, 'Any')
            
        out_any = False if curr_gender == 'Any' else True
        out_m = False if curr_gender == 'M' else True
        out_f = False if curr_gender == 'F' else True

        # 반환값 뒤에 버튼 3개의 상태(out_any, out_m, out_f)를 추가로 반환합니다.
        return True, seat_id, title, options, current_student, is_excluded, dash.no_update, dash.no_update, out_any, out_m, out_f

    # 2. 닫기 버튼을 누를 때
    elif tid == 'close-seat-modal-btn':
        return False, dash.no_update, dash.no_update, dash.no_update, dash.no_update, dash.no_update, dash.no_update, dash.no_update, dash.no_update, dash.no_update, dash.no_update

    # 3. 설정 변경 시 (학생 선택, 빈자리 체크, 성별 버튼 클릭) -> 즉시 저장 후 모달 닫기
    elif tid in ['seat-student-select', 'seat-exclude-check', 'btn-gender-any', 'btn-gender-m', 'btn-gender-f']:
        if not current_seat: raise PreventUpdate
        g_id, r, c = current_seat.split('-')
        key_short = f"{r}-{c}"

        for g in config:
            if str(g['id']) == g_id:
                if 'seats' not in g: g['seats'] = {}
                
                if tid == 'seat-exclude-check':
                    if exclude_val and key_short not in g['exclude']: g['exclude'].append(key_short)
                    elif not exclude_val and key_short in g['exclude']: g['exclude'].remove(key_short)
                
                elif tid == 'btn-gender-any': g['seats'][key_short] = 'Any'
                elif tid == 'btn-gender-m': g['seats'][key_short] = 'M'
                elif tid == 'btn-gender-f': g['seats'][key_short] = 'F'
                break

        if tid == 'seat-student-select':
            fixed_config = fixed_config or []
            for rule in fixed_config:
                if current_seat in rule.get('allowed', []):
                    rule['allowed'].remove(current_seat)

            if student_val:
                student_val = int(student_val)
                rule = next((r for r in fixed_config if r['no'] == student_val), None)
                if rule:
                    rule['allowed'] = [current_seat]
                    rule['forbidden'] = []
                    rule['direct'] = True 
                else:
                    std_name = next((s['이름'] for s in student_data if s['번호'] == student_val), "알수없음")
                    fixed_config.append({"no": student_val, "name": std_name, "allowed": [current_seat], "forbidden": [], "direct": True})

            fixed_config = [r for r in fixed_config if len(r.get('allowed', [])) > 0 or len(r.get('forbidden', [])) > 0]

        # 저장 후 모달이 닫히도록 리턴값 끝에 dash.no_update 3개 추가
        return False, dash.no_update, dash.no_update, dash.no_update, dash.no_update, dash.no_update, config, fixed_config, dash.no_update, dash.no_update, dash.no_update

    raise PreventUpdate


# --- [5. 최종 알고리즘] 자리 배치 계산 (특수 규칙 검증 엔진 포함) ---

# 👇 [추가됨] 번호순 배치를 위한 도우미 함수
def assign_by_number(student_data, config):
    """학생들을 번호순으로 정렬하여 열(Column) 방향으로 순서대로 배치합니다."""
    students = sorted(student_data or [], key=lambda x: int(x.get("번호", 0)))
    assigned_map = {}
    student_idx = 0
    num_students = len(students)
    
    for g in config:
        for c in range(g["cols"]): # 왼쪽 열부터
            for r in range(g["rows"]): # 위에서 아래로
                if student_idx >= num_students:
                    break
                key_short = f"{r}-{c}"
                if key_short in g.get("exclude", []):
                    continue
                seat_id = f"{g['id']}-{r}-{c}"
                assigned_map[seat_id] = students[student_idx]
                student_idx += 1
    return assigned_map


# generate_seats_logic 콜백 함수 내부 수정 (기존 로직에 추가)
@app.callback(
    [Output('assigned-map-store', 'data'), 
     Output('alert-container', 'children')], 
    [Input('generate-btn', 'n_clicks'), 
     Input('reset-btn', 'n_clicks'),
     Input('assign-number-btn', 'n_clicks')],
    [State('groups-config', 'data'),
     State('stored-data', 'data'),
     State('fixed-seats-config', 'data'),      # 👈 추가: 고정석 데이터
     State('special-rules-store', 'data'),     # 👈 추가: 짝꿍/밀집 방지 데이터 (에러 해결 핵심)
     State('placement-strategy', 'value')],       # 👈 추가: 배치 전략(동성/이성) 데이터
    prevent_initial_call=True
)
def generate_seats_logic(gen_n, reset_n, num_n, config, student_data, fixed_config, special_rules, strategy):
    # 이제 함수의 인자(parameter)로 special_rules를 받으므로 UnboundLocalError가 발생하지 않습니다.
    tid = ctx.triggered_id
    if not tid: raise PreventUpdate
    
    if tid == "reset-btn": return {}, dash.no_update 

    total_desks = sum([(g['rows'] * g['cols']) - len(g['exclude']) for g in config])
    if not student_data: return dash.no_update, dbc.Alert("학생 명단을 먼저 등록해주세요.", color="warning", dismissable=True, fade=True, duration=10000)
    elif len(student_data) > total_desks: return dash.no_update, dbc.Alert(f"책상 수가 부족합니다.", color="danger", dismissable=True, fade=True, duration=10000)

    if tid == "assign-number-btn":
        new_map = assign_by_number(student_data, config)
        return new_map, dash.no_update

    # --- 여기서부터 랜덤 배치 로직 ---
    # 데이터가 None일 경우를 대비해 기본값 설정
    special_rules = special_rules or {'no_pair': [], 'no_cluster': []}
    fixed_config = fixed_config or []
    strategy = strategy or "random" # 기본값 랜덤
    
    MAX_ATTEMPTS = 500
    for attempt in range(MAX_ATTEMPTS):
        assigned_map = {}
        m = [s for s in student_data if s.get('성별')=='남']
        f = [s for s in student_data if s.get('성별')=='여']
        random.shuffle(m)
        random.shuffle(f)
        
        all_available_seats = []
        for g in config:
            for r in range(g['rows']):
                for c in range(g['cols']):
                    if f"{r}-{c}" not in g['exclude']:
                        all_available_seats.append(f"{g['id']}-{r}-{c}")

        fixed_config_safe = fixed_config or []
        fixed_priority_students = [s for s in student_data if s['번호'] in [r['no'] for r in fixed_config_safe]]
        random.shuffle(fixed_priority_students)

        # 1. 고정석/금지석 먼저 배정
        for s_obj in fixed_priority_students:
            rule = next((r for r in fixed_config_safe if r['no'] == s_obj['번호']), None)
            if not rule: continue
            
            allowed = rule.get('allowed', [])
            forbidden = rule.get('forbidden', [])
            
            if allowed:
                possible_seats = [seat for seat in allowed if seat in all_available_seats and seat not in assigned_map]
            else:
                possible_seats = [seat for seat in all_available_seats if seat not in forbidden and seat not in assigned_map]
                
            if possible_seats:
                chosen_seat = random.choice(possible_seats)
                assigned_map[chosen_seat] = s_obj
                if s_obj in m: m.remove(s_obj)
                if s_obj in f: f.remove(s_obj)

        # 2. 남녀 전용석 배정
        s_m, s_f, s_any = [], [], []
        for g in config:
            for r in range(g['rows']):
                for c in range(g['cols']):
                    seat = f"{g['id']}-{r}-{c}"
                    if seat in all_available_seats and seat not in assigned_map:
                        stype = g['seats'].get(f"{r}-{c}", "Any")
                        if stype == "M": s_m.append(seat)
                        elif stype == "F": s_f.append(seat)
                        else: s_any.append(seat)

        for s in s_m: assigned_map[s] = m.pop() if m else None
        for s in s_f: assigned_map[s] = f.pop() if f else None

        # 3. 전략에 따른 나머지 좌석 배정
        triplets, pairs, solos = [], [], []
        s_any_set = set(s_any)
        
        for g in config:
            for r in range(g['rows']):
                segment = []
                for c in range(g['cols']):
                    seat = f"{g['id']}-{r}-{c}"
                    if seat in s_any_set: segment.append(seat)
                    else:
                        while len(segment) > 0:
                            if len(segment) == 3: triplets.append(tuple(segment)); segment = []
                            elif len(segment) >= 2: pairs.append(tuple(segment[:2])); segment = segment[2:]
                            else: solos.append(segment[0]); segment = []
                while len(segment) > 0:
                    if len(segment) == 3: triplets.append(tuple(segment)); segment = []
                    elif len(segment) >= 2: pairs.append(tuple(segment[:2])); segment = segment[2:]
                    else: solos.append(segment[0]); segment = []
        
        random.shuffle(triplets); random.shuffle(pairs)

        if strategy == "same":
            for t1, t2, t3 in triplets:
                if len(m) >= 3: assigned_map[t1], assigned_map[t2], assigned_map[t3] = m.pop(), m.pop(), m.pop()
                elif len(f) >= 3: assigned_map[t1], assigned_map[t2], assigned_map[t3] = f.pop(), f.pop(), f.pop()
                else: solos.extend([t1, t2, t3])
            for p1, p2 in pairs:
                if len(m) >= 2: assigned_map[p1], assigned_map[p2] = m.pop(), m.pop()
                elif len(f) >= 2: assigned_map[p1], assigned_map[p2] = f.pop(), f.pop()
                else: solos.extend([p1, p2])
        elif strategy == "diff":
            for t1, t2, t3 in triplets:
                if len(m) >= 2 and len(f) >= 1 and len(m) >= len(f): group = [m.pop(), m.pop(), f.pop()]
                elif len(f) >= 2 and len(m) >= 1: group = [f.pop(), f.pop(), m.pop()]
                elif len(m) >= 2 and len(f) >= 1: group = [m.pop(), m.pop(), f.pop()]
                else: group = []
                if group:
                    random.shuffle(group)
                    assigned_map[t1], assigned_map[t2], assigned_map[t3] = group[0], group[1], group[2]
                else: solos.extend([t1, t2, t3])
            for p1, p2 in pairs:
                if len(m) >= 1 and len(f) >= 1:
                    couple = [m.pop(), f.pop()]
                    random.shuffle(couple)
                    assigned_map[p1], assigned_map[p2] = couple[0], couple[1]
                else: solos.extend([p1, p2])
        else:
            for t1, t2, t3 in triplets: solos.extend([t1, t2, t3])
            for p1, p2 in pairs: solos.extend([p1, p2])

        rem = m + f
        random.shuffle(rem)
        for s in solos: assigned_map[s] = rem.pop() if rem else None

        # [검증 로직]
        is_valid = True
        pos_map = {v['번호']: k for k, v in assigned_map.items() if v}
        
        for pair in special_rules.get('no_pair', []):
            if pair[0] in pos_map and pair[1] in pos_map:
                g1, r1, c1 = map(int, pos_map[pair[0]].split('-'))
                g2, r2, c2 = map(int, pos_map[pair[1]].split('-'))
                if g1 == g2 and r1 == r2 and abs(c1 - c2) == 1:
                    is_valid = False; break
                    
        if is_valid:
            for cluster in special_rules.get('no_cluster', []):
                active = [s for s in cluster if s in pos_map]
                for i in range(len(active)):
                    for j in range(i+1, len(active)):
                        g1, r1, c1 = map(int, pos_map[active[i]].split('-'))
                        g2, r2, c2 = map(int, pos_map[active[j]].split('-'))
                        if g1 == g2 and abs(r1 - r2) <= 1 and abs(c1 - c2) <= 1:
                            is_valid = False; break
                    if not is_valid: break
                if not is_valid: break

        if is_valid:
            return assigned_map, dash.no_update

    error_msg = "🚨 설정된 규칙(고정석, 짝꿍, 밀집 방지)이 너무 까다로워 조건을 모두 만족하는 배치를 찾을 수 없습니다. 규칙을 조금 완화해 주세요."
    return dash.no_update, dbc.Alert(error_msg, color="danger", dismissable=True, className="fw-bold")

# --- [새 기능] 규칙 설정 모달 열고 닫기 ---
@app.callback(
    Output('rules-mgr-modal', 'is_open'),
    [Input('open-rules-mgr-btn', 'n_clicks'), Input('rules-mgr-close-btn', 'n_clicks')],
    State('rules-mgr-modal', 'is_open'), prevent_initial_call=True
)
def toggle_rules_modal(n1, n2, is_open):
    return not is_open

# --- [수정] 짝꿍 방지 드롭다운 명단만 업데이트 하도록 변경 ---
@app.callback(
    [Output('no-pair-1', 'options'), 
     Output('no-pair-2', 'options')],
    [Input('stored-data', 'data')] # 💡 빠졌던 Input 추가
)
def update_rules_dropdowns(students):
    if not students: 
        return [], []
    opts = [{"label": f"{s['번호']}번 {s['이름']}", "value": s['번호']} for s in students]
    return opts, opts # 💡 기존 3개에서 2개로 변경

# --- [수정] 짝꿍/밀집 방지 규칙 저장 및 표 그리기 ---
@app.callback(
    Output('special-rules-store', 'data'),
    Output('no-pair-list', 'children'),
    Output('no-cluster-list', 'children'),
    Output('no-pair-1', 'value'), 
    Output('no-pair-2', 'value'),
    Output('temp-cluster-selection', 'data', allow_duplicate=True),  # 규칙 추가 후 선택 목록 초기화
    [Input('add-no-pair-btn', 'n_clicks'), 
     Input('add-no-cluster-btn', 'n_clicks'), 
     Input({'type': 'del-rule', 'rtype': ALL, 'idx': ALL}, 'n_clicks')],
    [State('no-pair-1', 'value'), 
     State('no-pair-2', 'value'), 
     State('temp-cluster-selection', 'data'), 
     State('special-rules-store', 'data'),
     State('stored-data', 'data')],
    prevent_initial_call=True
)
def manage_special_rules(btn_pair, btn_cluster, del_n, p1, p2, cluster_vals, rules_data, students):
    tid = ctx.triggered_id
    rules_data = rules_data or {'no_pair': [], 'no_cluster': []}
    
    # 1. 짝꿍 방지 추가 (기존 로직)
    if tid == 'add-no-pair-btn' and p1 and p2 and p1 != p2:
        rules_data['no_pair'].append([p1, p2])
        
    # 2. 밀집 방지 추가 (버튼 그리드에서 선택된 이름 리스트 저장)
    elif tid == 'add-no-cluster-btn' and cluster_vals and len(cluster_vals) >= 2:
        # 번호로 관리하기 위해 이름 -> 번호로 변환하여 저장
        selected_nos = []
        for name in cluster_vals:
            s_node = next((s for s in students if s['이름'] == name), None)
            if s_node: selected_nos.append(s_node['번호'])
        if len(selected_nos) >= 2:
            rules_data['no_cluster'].append(selected_nos)
            
    # 3. 삭제 로직
    elif isinstance(tid, dict) and tid.get('type') == 'del-rule':
        rtype, idx = tid['rtype'], tid['idx']
        if rtype in rules_data and len(rules_data[rtype]) > idx:
            rules_data[rtype].pop(idx)
            
    def get_name(no): return next((s['이름'] for s in students if s['번호'] == no), str(no))
    
    # 짝꿍 방지 테이블 생성 (다크모드 대응을 위해 bg-white 제거)
    pair_rows = []
    for i, p in enumerate(rules_data.get('no_pair', [])):
        pair_rows.append(html.Tr([
            html.Td(f"{p[0]}번 {get_name(p[0])} ↔ {p[1]}번 {get_name(p[1])}", className="align-middle"),
            html.Td(dbc.Button("삭제", id={'type':'del-rule', 'rtype':'no_pair', 'idx':i}, size="sm", color="danger", outline=True))
        ]))
    pair_table = dbc.Table([html.Tbody(pair_rows)], size="sm", bordered=True) if pair_rows else html.P("등록된 규칙이 없습니다.", className="text-muted small")
    
    # 밀집 방지 테이블 생성
    cluster_rows = []
    for i, c in enumerate(rules_data.get('no_cluster', [])):
        names = ", ".join([f"{no}번 {get_name(no)}" for no in c])
        cluster_rows.append(html.Tr([
            html.Td(names, className="align-middle"),
            html.Td(dbc.Button("삭제", id={'type':'del-rule', 'rtype':'no_cluster', 'idx':i}, size="sm", color="danger", outline=True))
        ]))
    cluster_table = dbc.Table([html.Tbody(cluster_rows)], size="sm", bordered=True) if cluster_rows else html.P("등록된 규칙이 없습니다.", className="text-muted small")

    if tid in ('add-no-pair-btn', 'add-no-cluster-btn') or (isinstance(tid, dict) and tid.get('type') == 'del-rule'):
        clear_sel = []
    else:
        clear_sel = dash.no_update
    return rules_data, pair_table, cluster_table, None, None, clear_sel

# --- [새 기능] 교실 레이아웃 헤더에 학생 통계 텍스트 표시 ---
@app.callback(
    Output("student-stats-display", "children"),
    Input("stored-data", "data")
)
def update_student_stats_text(student_data):
    if not student_data:
        return "(등록된 학생 없음)"
    
    total = len(student_data)
    male = len([s for s in student_data if s.get('성별') == '남'])
    female = len([s for s in student_data if s.get('성별') == '여'])
    
    # 선생님이 요청하신 괄호 텍스트 포맷으로 반환합니다.
    return f"(학생수: {total}명, 남학생: {male}명, 여학생: {female}명)"

# --- [새 기능] 개별 좌석 모달의 '빈자리' 토글 버튼 텍스트 자동 변경 ---
@app.callback(
    Output('seat-exclude-check', 'label'),
    Input('seat-exclude-check', 'value')
)
def update_exclude_btn_label(is_excluded):
    # 빈자리로 설정된 상태(True)이면 '해제' 문구를, 아니면 '설정' 문구를 보여줍니다.
    if is_excluded:
        return "✅ 빈자리 해제"
    else:
        return "🚫 빈 자리로 설정"

# --- [새 기능] 엑셀 업로드 시 파일명 표시 콜백 ---
@app.callback(
    Output('upload-filename-display', 'children'),
    Input('upload-data', 'filename'),
    prevent_initial_call=True
)
def display_uploaded_filename(filename):
    if filename:
        # 💡 수정된 부분: 요구하신 대로 '파일명: ' 이라는 텍스트를 괄호 안에 추가했습니다.
        return f"(파일명: {filename})"
    return ""

# --- 사이드바 및 메인 레이아웃 통합 토글 로직 ---
@app.callback(
    [Output("sidebar", "style"),
     Output("main-title", "style"),
     Output("sidebar-content", "style"),
     Output("main-col", "style"),
     Output("toggle-sidebar-btn", "title")], # 💡 1. 툴팁 텍스트를 변경하기 위한 Output 추가!
    [Input("toggle-sidebar-btn", "n_clicks")],
    [State("sidebar", "style"),
     State("main-title", "style"),
     State("sidebar-content", "style"),
     State("main-col", "style")],
    prevent_initial_call=True
)
def toggle_sidebar(n, sidebar_style, title_style, content_style, main_col_style):
    new_sidebar_style = sidebar_style.copy() if sidebar_style else {}
    new_title_style = title_style.copy() if title_style else {"transition": "margin-left 0.4s ease-in-out"}
    new_content_style = content_style.copy() if content_style else {"transition": "opacity 0.2s"}
    new_main_col_style = main_col_style.copy() if main_col_style else {"flex": "1", "transition": "margin-left 0.4s"}
    
    # [사이드바 열기] 너비 60px -> 300px
    if new_sidebar_style.get("width", "80px") in ["60px", "80px"]:
        new_sidebar_style["width"] = "300px"
        new_title_style["marginLeft"] = "320px"
        new_content_style["opacity"] = "1"
        new_content_style["visibility"] = "visible"
        new_main_col_style["marginLeft"] = "320px"
        
        # 💡 사이드바가 열려있으므로 다음에 누를 땐 접히게 됨 -> "메뉴 접기" 텍스트 할당
        btn_title = "메뉴 접기"
        
    # [사이드바 접기] 너비 300px -> 60px
    else:
        new_sidebar_style["width"] = "80px"
        new_title_style["marginLeft"] = "90px"
        new_content_style["opacity"] = "0"
        new_content_style["visibility"] = "hidden"
        new_main_col_style["marginLeft"] = "90px"
        
        # 💡 사이드바가 닫혀있으므로 다음에 누를 땐 펼쳐지게 됨 -> "메뉴 펼치기" 텍스트 할당
        btn_title = "메뉴 펼치기"
        
    # 💡 5개의 값을 반환 (마지막 btn_title이 버튼의 title 속성으로 들어감)
    return new_sidebar_style, new_title_style, new_content_style, new_main_col_style, btn_title


@app.callback(
    Output("main-wrapper", "style"),
    Input("theme-switch", "value")
)
def toggle_theme_colors(is_dark):
    if is_dark:
        # 🌙 다크 모드
        return {
            "--main-bg": "#131314",
            "--bar-bg": "#1E1F20",
            "--modal-bg": "#242526",       # 모달창 배경
            "--input-bg": "#2A2B2D",       # 입력 박스/카드 배경
            "--border-color": "#3E4042",
            "--text-color": "#E3E3E3",
            "--btn-bg": "#3A3B3C",
            "--btn-text": "#E3E3E3",
            "--btn-hover-bg": "#4E4F50",
            "backgroundColor": "var(--main-bg)",
            "color": "var(--text-color)",
            "minHeight": "100vh",
            "transition": "background-color 0.4s ease"
        }
    else:
        # ☀️ 라이트 모드
        return {
            "--main-bg": "#FFFFFF",
            "--bar-bg": "#F0F4F9",
            "--modal-bg": "#FFFFFF",
            "--input-bg": "#F8F9FA",
            "--border-color": "#DEE2E6",
            "--text-color": "#1F1F1F",
            "--btn-bg": "#FFFFFF",
            "--btn-text": "#1F1F1F",
            "--btn-hover-bg": "#E9ECEF",
            "backgroundColor": "var(--main-bg)",
            "color": "var(--text-color)",
            "minHeight": "100vh",
            "transition": "background-color 0.4s ease"
        }


# ✅ 버튼 생성: 항상 회색(선택 안 됨)으로 시작
@app.callback(
    [Output('cluster-selection-grid', 'children'),
     Output('temp-cluster-selection', 'data', allow_duplicate=True)],
    [Input('rules-mgr-modal', 'is_open'),
     Input('stored-data', 'data')],
    prevent_initial_call=True
)
def update_student_grid_for_rules(is_open, student_data):
    if not is_open or not student_data:
        return [], []
    
    sorted_students = sorted(student_data, key=lambda x: int(x.get('번호', 0)))
    
    buttons = []
    for s in sorted_students:
        name = s.get('이름', '')
        buttons.append(
            dbc.Button(
                f"{s.get('번호')}. {name}",
                id={'type': 'cluster-btn', 'name': name},
                color="secondary",
                outline=True,
                className="p-2 fw-bold",
                style={"pointerEvents": "auto", "userSelect": "none", "cursor": "pointer"}
            )
        )
    # 버튼 생성과 동시에 선택 초기화
    return buttons, []

# ✅ 버튼 색상 변경 콜백 (선택 상태만 반영, 버튼 자체는 재생성 안 함)
@app.callback(
    [Output({'type': 'cluster-btn', 'name': ALL}, 'color'),
     Output({'type': 'cluster-btn', 'name': ALL}, 'outline')],
    [Input('temp-cluster-selection', 'data')],
    [State({'type': 'cluster-btn', 'name': ALL}, 'id')]
)
def update_button_styles(current_selection, btn_ids):
    if not btn_ids:
        raise dash.exceptions.PreventUpdate
    
    current_selection = current_selection if isinstance(current_selection, list) else []
    
    colors = []
    outlines = []
    for bid in btn_ids:
        if bid['name'] in current_selection:
            colors.append("primary")
            outlines.append(False)
        else:
            colors.append("secondary")
            outlines.append(True)
    return colors, outlines

# ✅ 초기화 버튼 클릭 시 선택 초기화
@app.callback(
    Output('temp-cluster-selection', 'data', allow_duplicate=True),
    Input('clear-cluster-temp-btn', 'n_clicks'),
    prevent_initial_call=True
)
def clear_selection_on_button_click(n_clicks):
    # 초기화 버튼 클릭 시
    return []

# ✅ 버튼 클릭 시 선택 토글
@app.callback(
    Output('temp-cluster-selection', 'data', allow_duplicate=True),
    [Input({'type': 'cluster-btn', 'name': ALL}, 'n_clicks')],
    [State('temp-cluster-selection', 'data')],
    prevent_initial_call=True
)
def toggle_student_selection(n_clicks_list, current_selection):
    tid = ctx.triggered_id
    
    if not tid or not isinstance(tid, dict) or tid.get('type') != 'cluster-btn':
        raise dash.exceptions.PreventUpdate
    
    current_selection = current_selection if isinstance(current_selection, list) else []
    clicked_name = tid['name']
    
    if clicked_name in current_selection:
        current_selection.remove(clicked_name)
    else:
        current_selection.append(clicked_name)
    
    return current_selection



# --- 6. 레이아웃 렌더링 ---

@app.callback(
    Output('main-layout-preview', 'children'),
    Input('groups-config', 'data'),
    Input('assigned-map-store', 'data'),
    Input('fixed-seats-config', 'data'),
    State('stored-data', 'data')
)
def render_layout(config, assigned_map, fixed_config, student_data):
    assigned_map = assigned_map or {}
    
    # 1. 기존 분단(책상) 레이아웃 생성
    layout = dbc.Row([
        dbc.Col([
            html.Div([
                html.B(f"{g['id']}분단 "),
                dbc.Button(
                    "✏️", 
                    id={'type': 'open-edit', 'index': g['id']}, 
                    size="sm", 
                    color="link", 
                    title="분단 세부 설정",          # 💡 마우스 호버 시 뜨는 텍스트(툴팁) 설정
                    className="edit-icon-btn",       # 💡 CSS 효과를 주기 위한 이름표 추가
                    style={"textDecoration": "none"}
                ),
                html.Div([
                    dbc.Row([
                        dbc.Col(render_seat(g, r, c, assigned_map, fixed_config, student_data), width=True, className="p-1")
                        for c in range(g['cols'])
                    ], className="g-0") for r in range(g['rows'])
                # 💡 수정된 부분: bg-body와 고정 style을 지우고, 'cluster-box' 클래스 추가, 패딩은 p-3으로 늘림
                ], className="border p-3 rounded shadow-sm cluster-box") 
            ])
        ], width={"size": True}) for g in config
    ], className="g-3 justify-content-center")

    # 2. [새로 추가된 부분] 칠판 디자인 생성! (기존 유지)
    chalkboard = html.Div([
        html.Span("👨‍🏫 칠 판", className="fw-bold")
    ], style={
        "backgroundColor": "#2C4C3B", # 진짜 칠판 느낌의 짙은 녹색
        "color": "white",
        "border": "6px solid #8B5A2B", # 우드 톤의 갈색 테두리
        "borderRadius": "8px",
        "width": "60%",               # 가로 길이 적당히 조절
        "maxWidth": "600px",
        "margin": "0 auto 30px auto", # 정중앙에 배치하고 책상과 30px 띄움
        "padding": "12px",
        "textAlign": "center",
        "fontSize": "1.2rem",
        "boxShadow": "0px 4px 6px rgba(0,0,0,0.2)" # 예쁜 그림자
    })

    # 3. [수정된 반환값] 칠판을 맨 위에 올리고, 그 밑에 책상(layout)을 깔아서 한 번에 반환합니다! (기존 유지)
    return html.Div([
        chalkboard, 
        layout      
    ])

def render_seat(g, r, c, assigned_map, fixed_config, student_data):
    key_short = f"{r}-{c}"
    seat_id = f"{g['id']}-{r}-{c}"
    
    # [1. 빈자리(통로) 처리]
    if key_short in g['exclude']: 
        return html.Div([
            html.Div(
                html.Div("🚫 빈자리", style={"fontWeight": "bold", "fontSize": "0.85rem", "color": "#adb5bd"}),
                id={'type': 'seat-click', 'pos': seat_id},
                n_clicks=0,
                style={"flex": "1", "display": "flex", "alignItems": "center", "justifyContent": "center", "cursor": "pointer"}
            )
        ], className="border rounded text-center bg-light shadow-sm", style={"height": "60px", "display": "flex", "flexDirection": "column", "padding": "3px", "transition": "0.2s"})
    
    student = assigned_map.get(seat_id)
    curr_gender = g['seats'].get(key_short, "Any")
    is_pre_assigned = False

    # 고정석 확인 로직 변경 (자리배치 전/후 모두 체크)
    if fixed_config:
        # 이 책상(seat_id)에 걸려있는 고정석 룰이 있는지 확인
        fixed_rule = next((rule for rule in fixed_config if seat_id in rule.get('allowed', [])), None)
        
        if fixed_rule and fixed_rule.get('direct') is True:
            # 1. 자리 배치 실행 후: 이미 배정된 학생이 고정석 학생과 일치하면 핀 유지
            if student and student['번호'] == fixed_rule['no']:
                is_pre_assigned = True
            # 2. 자리 배치 실행 전 (미리보기): 빈자리일 때 학생 정보를 불러와서 앉혀둠
            elif not student and student_data:
                student = next((s for s in student_data if s['번호'] == fixed_rule['no']), None)
                is_pre_assigned = True

    # 책상의 기본 스타일 (높이를 60px로 줄여서 6줄까지 표시 가능하게)
    seat_style = {
        "position": "relative",
        "height": "60px", 
        "display": "flex", 
        "flexDirection": "column", 
        "padding": "3px", 
        "transition": "0.2s"
    }
    
    text_color = "inherit" # 기본 글자색 (테마에 따름)

    # [2. 학생이 배정된 경우]
    if student:
        display_text = f"{student['번호']}. {student['이름']}"
        
        bg = "" # 기존 text-dark 클래스 충돌을 막기 위해 비워줍니다.
        seat_style["backgroundColor"] = "#AED6F1" if student['성별']=='남' else "#F5B7B1"  # 파스텔 블루, 파스텔 핑크
        
        # 💡 [글자색 추가] 학생이 배정된 자리의 글자색을 아주 진한 검정/회색 톤으로 강제 고정합니다.
        text_color = "#212529" # 완전한 검정색을 원하시면 "#000000"으로 변경하셔도 됩니다.
        
        border_class = "border-warning border-4 shadow-lg" if is_pre_assigned else "border shadow-sm"
        
    # [3. 학생이 없는 빈 책상인 경우 (성별 전용석 설정 확인)]
    else:
        bg = "bg-body" # 다크모드 대응
        border_class = "border shadow-sm"
        
        if curr_gender == 'M': 
            display_text = "남학생 자리"
            bg = "" # 💡 [추가] 기존 bg-body 속성을 비워주어야 색상이 적용됩니다!
            seat_style["backgroundColor"] = "#E6F0FA" # 연한 파란색 배경
            text_color = "#004085"                    # 진한 파란색 텍스트
        elif curr_gender == 'F': 
            display_text = "여학생 자리"
            bg = "" # 💡 [추가] 기존 bg-body 속성을 비워주어야 색상이 적용됩니다!
            seat_style["backgroundColor"] = "#FAE6EA" # 연한 분홍색 배경
            text_color = "#721C24"                    # 진한 붉은색 텍스트
        else: 
            display_text = "성별 무관"

   # 책상 안에 들어갈 내용물(이름)
    inner_children = [
        html.Div(display_text, style={"fontWeight": "bold", "fontSize": "1.1rem", "color": text_color})
    ]

    # 💡 [추가] 고정석인 경우 우측 상단에 압정(핀) 아이콘 띄우기
    if is_pre_assigned:
        inner_children.append(
            html.Div("📌", style={"position": "absolute", "top": "2px", "right": "4px", "fontSize": "0.85rem"})
        )

    # 최종 렌더링
    return html.Div([
        html.Div(
            inner_children, 
            id={'type': 'seat-click', 'pos': seat_id},
            n_clicks=0,
            style={"flex": "1", "display": "flex", "alignItems": "center", "justifyContent": "center", "cursor": "pointer"}
        )
    # 💡 className 끝에 'fade-in-effect'를 띄어쓰기와 함께 추가했습니다!
    ], className=f"{border_class} rounded text-center {bg} seat-hover-effect fade-in-effect", style=seat_style, key=f"seat-{seat_id}-{time.time()}")

@app.callback(
    Output("print-modal", "is_open"),
    Input("print-btn", "n_clicks"),
    prevent_initial_call=True,
)
def open_print_modal(n):
    return True


# ─────────────────────────────────────────────────────────────
# [인쇄 기능] 1-b. 취소/인쇄 버튼 → 모달 닫기
# ─────────────────────────────────────────────────────────────
@app.callback(
    Output("print-modal", "is_open", allow_duplicate=True),
    [Input("print-modal-close-btn", "n_clicks"),
     Input("do-print-btn", "n_clicks")],
    prevent_initial_call=True,
)
def close_print_modal(close_n, do_n):
    return False


# ─────────────────────────────────────────────────────────────
# [인쇄 기능] 2. 인쇄용 HTML 생성 (서버 콜백)
# ─────────────────────────────────────────────────────────────
def _build_print_html(orientation, options, config, assigned_map, student_data):
    """분단 텍스트 제거 및 명렬표 가독성 개선 버전"""
    assigned_map = assigned_map or {}
    config      = config or []
    students     = sorted(student_data or [], key=lambda x: int(x.get("번호", 0)))
    include_roster = "roster" in (options or [])

    # 180도 회전 및 정렬 로직
    if orientation == "teacher":
        ordered_config = list(reversed(config))
        row_order_func = lambda r_count: range(r_count - 1, -1, -1)
        col_order_func = lambda c_count: range(c_count - 1, -1, -1)
        group_align = "flex-end" # 칠판(아래) 쪽으로 1행 맞춤
    else:
        ordered_config = config
        row_order_func = lambda r_count: range(r_count)
        col_order_func = lambda c_count: range(c_count)
        group_align = "flex-start" # 칠판(위) 쪽으로 1행 맞춤

    # ── 좌석 그리드 HTML 생성 (분단 타이틀 제거) ──
    groups_html = ""
    for g in ordered_config:
        rows_count = g["rows"]
        cols_count = g["cols"]
        exclude    = g.get("exclude", [])

        row_order = row_order_func(rows_count)
        col_order = col_order_func(cols_count)

        # 'group-title' 부분이 삭제되었습니다.
        group_html = f"<div class='group-wrap'><table class='seat-tbl'>"
        for r in row_order:
            group_html += "<tr>"
            for c in col_order:
                key_short = f"{r}-{c}"
                seat_id   = f"{g['id']}-{r}-{c}"

                if key_short in exclude:
                    group_html += "<td class='seat seat-empty'>빈자리</td>"
                else:
                    student = assigned_map.get(seat_id)
                    if student:
                        cls = "seat-male" if student.get("성별") == "남" else "seat-female"
                        group_html += (
                            f"<td class='seat {cls}'>"
                            f"<span class='stu-info'>{student['번호']}. {student['이름']}</span>"
                            f"</td>"
                        )
                    else:
                        group_html += "<td class='seat seat-vacant'></td>"
            group_html += "</tr>"
        group_html += "</table></div>"
        groups_html += group_html

    # ── 명렬표 HTML 생성 (폰트 크기 및 높이 조정) ──
    roster_html = ""
    if include_roster and students:
        rows_html = "".join(
            f"<tr><td>{s['번호']}</td><td class='roster-name'>{s['이름']}</td></tr>"
            for s in students
        )
        roster_html = (
            f"<div class='roster-wrap'>"
            f"<table class='roster-tbl'>"
            f"<thead><tr><th>번호</th><th>이름</th></tr></thead>"
            f"<tbody>{rows_html}</tbody>"
            f"</table></div>"
        )

    board_label = "📋 칠 판"
    board_top = f"<div class='chalkboard chalkboard-top'>{board_label}</div>" if orientation == "student" else ""
    board_bottom = f"<div class='chalkboard chalkboard-bottom'>{board_label}</div>" if orientation == "teacher" else ""
    view_label = "교사 기준" if orientation == "teacher" else "학생 기준"

    return f"""<!DOCTYPE html>
<html lang="ko">
<head>
<meta charset="UTF-8">
<style>
  * {{ box-sizing: border-box; margin: 0; padding: 0; }}
  body {{
    font-family: 'Malgun Gothic', '맑은 고딕', Arial, sans-serif;
    padding: 15px;
    background: #fff;
    display: flex;
    flex-direction: column;
    align-items: center;
  }}
  
  /* 💡 1. h2 상단 마진을 0으로 설정하여 명렬표 상단과 딱 맞물리도록 수정 */
  h2.print-title {{ font-size: 1.3rem; margin: 0 0 20px 0; font-weight: bold; }}

  .layout-container {{
    display: flex;
    width: 100%;
    justify-content: center;
    align-items: flex-start;
    gap: 30px;
  }}

  .main-content {{ display: flex; flex-direction: column; align-items: center; flex: 1; }}

  .chalkboard {{
    background: #2C4C3B; color: #fff;
    border: 5px solid #8B5A2B; border-radius: 8px;
    padding: 10px; text-align: center; font-weight: bold; font-size: 1.2rem; width: 400px;
  }}
  
  .chalkboard-top {{ margin-bottom: 30px; }}
  .chalkboard-bottom {{ margin-top: 30px; }}

  .groups-container {{
    display: flex; gap: 20px; justify-content: center;
    align-items: {group_align};
  }}

  .seat-tbl {{ border-collapse: collapse; }}
  .seat {{
    width: 125px; height: 70px;
    border: 2px solid #333; text-align: center; vertical-align: middle;
  }}
  .stu-info {{ font-size: 1.1rem; font-weight: bold; color: #1F1F1F; }}
  .seat-male {{ background: #AED6F1; }}
  .seat-female {{ background: #F5B7B1; }}
  .seat-empty {{ background: #F5F5F5; color: #BBB; font-size: 0.8rem; }}

  .roster-wrap {{ flex-shrink: 0; }}
  .roster-tbl {{
    border-collapse: collapse;
    width: 130px; 
    border-top: 2px solid #444; 
  }}
  .roster-tbl th, .roster-tbl td {{
    border: 1px solid #444;
    padding: 2px 1px; 
    text-align: center;
    font-size: 0.7rem; 
    height: 15px; 
  }}
  .roster-tbl th {{ background: #EEE; font-weight: bold; font-size: 0.9rem; }}

  @media print {{
    body {{ padding: 0; }}
    @page {{ margin: 10mm; size: A4 landscape; }}
  }}
</style>
</head>
<body>
  <div class="layout-container">
    <div class="main-content">
      <h2 class="print-title">&lt; 학급 자리표 ({view_label}) &gt;</h2>
      {board_top}
      <div class="groups-container">{groups_html}</div>
      {board_bottom}
    </div>
    {roster_html}
  </div>
</body>
</html>"""


@app.callback(
    Output("print-html-store", "data"),
    Input("do-print-btn", "n_clicks"),
    State("print-orientation", "value"),
    State("print-options", "value"),
    State("groups-config", "data"),
    State("assigned-map-store", "data"),
    State("stored-data", "data"),
    prevent_initial_call=True,
)
def generate_print_content(n_clicks, orientation, options, config, assigned_map, student_data):
    if not n_clicks:
        raise PreventUpdate
    return _build_print_html(orientation, options, config, assigned_map, student_data)


# ─────────────────────────────────────────────────────────────
# [인쇄 기능] 3. 클라이언트 사이드: 숨겨진 iframe으로 바로 인쇄
# ─────────────────────────────────────────────────────────────
app.clientside_callback(
    """function(html_content) {
        if (!html_content) {
            return window.dash_clientside.no_update;
        }
        var iframe = document.getElementById('hidden-print-iframe');
        if (!iframe) {
            iframe = document.createElement('iframe');
            iframe.id = 'hidden-print-iframe';
            iframe.style.position = 'fixed';
            iframe.style.right = '0';
            iframe.style.bottom = '0';
            iframe.style.width = '0';
            iframe.style.height = '0';
            iframe.style.border = '0';
            document.body.appendChild(iframe);
        }
        var doc = iframe.contentWindow.document;
        doc.open();
        doc.write(html_content);
        doc.close();
        
        setTimeout(function() {
            iframe.contentWindow.focus();
            iframe.contentWindow.print();
        }, 500);
        
        return window.dash_clientside.no_update;
    }""",
    Output("print-trigger-dummy", "children"),
    Input("print-html-store", "data"),
    prevent_initial_call=True
)


# --- [새 기능] 다크모드/라이트모드 전환 스위치 콜백 ---
app.clientside_callback(
    """
    function(is_dark) {
        if (is_dark) {
            document.documentElement.setAttribute('data-bs-theme', 'dark');
        } else {
            document.documentElement.setAttribute('data-bs-theme', 'light');
        }
        return window.dash_clientside.no_update;
    }
    """,
    Output("blank-output", "children"),
    Input("theme-switch", "value")
)

# --- [자리 배치 결과 저장 기능] ---
@app.callback(
    Output('seating-save-modal', 'is_open'),
    Output('current-seating-result', 'data'),
    Input('assigned-map-store', 'data'),
    State('seating-save-modal', 'is_open'),
    prevent_initial_call=True
)
def show_seating_save_modal(assigned_map, is_open):
    """자리 배치 완료 시 저장 모달 자동 표시"""
    if not assigned_map or assigned_map == {}:
        return dash.no_update, dash.no_update
    # 모달 열기 + 현재 배치 결과 저장
    return True, assigned_map

# 저장된 배치 목록 표시
@app.callback(
    Output('seating-results-list', 'children'),
    Input('seating-results-store', 'data')
)
def update_seating_results_list(results):
    """저장된 배치 결과 목록 표시"""
    if not results:
        return dbc.Alert("저장된 배치가 없습니다.", color="info", className="mb-0")
    
    items = []
    for idx, result in enumerate(results):
        name = result.get('name', f'배치 {idx+1}')
        timestamp = result.get('timestamp', 'N/A')
        items.append(
            dbc.Card([
                dbc.CardBody([
                    html.H6(name, className="mb-1"),
                    html.Small(timestamp, className="text-muted"),
                    dbc.Button("불러오기", id={'type': 'load-seating-btn', 'index': idx}, 
                              color="info", size="sm", className="mt-2 me-2"),
                    dbc.Button("삭제", id={'type': 'delete-seating-btn', 'index': idx}, 
                              color="danger", size="sm", className="mt-2"),
                ])
            ], className="mb-2", style={"backgroundColor": "var(--card-bg)"})
        )
    return items

# 저장하기 클릭
@app.callback(
    Output('seating-results-store', 'data'),
    Output('seating-save-modal', 'is_open'),
    Input('save-seating-result-btn', 'n_clicks'),
    [State('seating-results-store', 'data'),
     State('current-seating-result', 'data'),
     State('seating-save-name', 'value')],
    prevent_initial_call=True
)
def save_seating_result(n_clicks, results, current_result, save_name):
    """현재 배치 결과를 저장소에 저장"""
    import datetime
    if not current_result:
        raise PreventUpdate
    
    results = results or []
    new_result = {
        'data': current_result,
        'name': save_name or f"배치 {len(results)+1}",
        'timestamp': datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    }
    results.append(new_result)
    return results, False

# 취소 버튼
@app.callback(
    Output('seating-save-modal', 'is_open'),
    Input('cancel-save-seating-btn', 'n_clicks'),
    prevent_initial_call=True
)
def close_seating_modal(n_clicks):
    return False

# 백업 다운로드
@app.callback(
    Output('download-seating-backup', 'data'),
    Input('backup-seating-btn', 'n_clicks'),
    State('seating-results-store', 'data'),
    prevent_initial_call=True
)
def download_seating_backup(n_clicks, results):
    """저장된 모든 배치 결과를 JSON으로 다운로드"""
    import json
    import datetime
    
    backup_data = {
        'backup_date': datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        'results': results or []
    }
    return dict(content=json.dumps(backup_data, ensure_ascii=False, indent=2), filename="자리배치_백업.json")

# 저장된 배치 불러오기
@app.callback(
    Output('assigned-map-store', 'data'),
    Output('seating-save-modal', 'is_open'),
    Input({'type': 'load-seating-btn', 'index': ALL}, 'n_clicks'),
    State('seating-results-store', 'data'),
    prevent_initial_call=True
)
def load_seating_result(n_clicks, results):
    """저장된 배치 결과 불러오기"""
    if not any(n_clicks):
        raise PreventUpdate
    
    idx = ctx.triggered_id['index']
    if idx < len(results):
        loaded_result = results[idx]['data']
        return loaded_result, False
    raise PreventUpdate

# 저장된 배치 삭제
@app.callback(
    Output('seating-results-store', 'data'),
    Input({'type': 'delete-seating-btn', 'index': ALL}, 'n_clicks'),
    State('seating-results-store', 'data'),
    prevent_initial_call=True
)
def delete_seating_result(n_clicks, results):
    """저장된 배치 결과 삭제"""
    if not any(n_clicks):
        raise PreventUpdate
    
    idx = ctx.triggered_id['index']
    results = results or []
    if idx < len(results):
        results.pop(idx)
    return results

# 배치 결과 관리 버튼 (모달 열기)
@app.callback(
    Output('seating-save-modal', 'is_open'),
    Input('open-seating-result-btn', 'n_clicks'),
    State('seating-save-modal', 'is_open'),
    prevent_initial_call=True
)
def toggle_seating_result_modal(n_clicks, is_open):
    """배치 결과 관리 모달 열기/닫기"""
    return not is_open

# ─────────────────────────────────────────────────────────────
# [서버 실행] 반드시 파일의 "맨 마지막"에 위치!
# ─────────────────────────────────────────────────────────────
if __name__ == "__main__":
    import os
    debug_mode = os.getenv('DEBUG', 'False') == 'True'
    app.run(debug=debug_mode, host='0.0.0.0', port=int(os.getenv('PORT', 8050)))