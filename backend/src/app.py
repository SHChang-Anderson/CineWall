import httpx
from nicegui import ui
import asyncio

# --- 設定 ---
API_BASE_URL = "http://localhost:8000"

class CineWallUI:
    def __init__(self):
        self.movies = []
        self.loading = False

    async def update_poster(self, movie):
        """背景抓取海報並即時更新 UI"""
        try:
            from urllib.parse import quote
            async with httpx.AsyncClient(timeout=10.0) as client:
                # 使用 quote 確保中文字元與特殊符號被正確編碼
                safe_title = quote(movie['title'])
                url = f"{API_BASE_URL}/movie/{safe_title}/poster?year={movie['year'] or ''}"
                response = await client.get(url)
                if response.status_code == 200:
                    data = response.json()
                    movie['poster_url'] = data.get('poster_url')
                    # 抓到一張就更新一次 UI
                    self.render_wall.refresh()
        except Exception as e:
            print(f"Poster fetch error for {movie['title']}: {e}")

    async def fetch_movies(self):
        self.loading = True
        ui.notify('正在從後端獲取影片清單...', type='info')
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                # 1. 先抓取基礎清單 (不含海報)
                response = await client.get(f"{API_BASE_URL}/movies/gdrive?folder=movie")
                if response.status_code == 200:
                    self.movies = response.json()
                    # 初始化海報為佔位圖
                    for m in self.movies:
                        m['poster_url'] = 'https://via.placeholder.com/220x330?text=Loading...'
                    
                    # 2. 立即渲染 UI 牆面
                    self.render_wall.refresh()
                    ui.notify(f'清單已載入，正在背景抓取 {len(self.movies)} 張海報', type='positive')

                    # 3. 同時發起所有海報抓取任務 (並行處理)
                    for movie in self.movies:
                        asyncio.create_task(self.update_poster(movie))
                else:
                    ui.notify(f'後端錯誤: {response.status_code}', type='negative')
        except Exception as e:
            ui.notify(f'無法連接到後端伺服器: {e}', type='negative')
        finally:
            self.loading = False
            self.render_wall.refresh()

    @ui.refreshable
    def render_wall(self):
        if not self.movies:
            with ui.column().classes('w-full items-center mt-32'):
                ui.icon('movie_filter', size='80px').classes('text-gray-600')
                ui.label('尚未掃描或資料夾為空').classes('text-xl text-gray-500')
                ui.label('請確保 Google Drive 中有名為 "movie" 的資料夾且含有影片').classes('text-sm text-gray-600')
            return

        # 網格佈局
        with ui.grid(columns='repeat(auto-fill, minmax(220px, 1fr))').classes('w-full gap-6 p-8'):
            for movie in self.movies:
                self.movie_card(movie)

    def movie_card(self, movie):
        # 建立卡片並綁定點擊事件
        with ui.card().tight().classes('bg-[#1e1e1e] border border-gray-800 hover:border-blue-500 transition-all transform hover:-translate-y-1 cursor-pointer') \
            .on('click', lambda: self.play_video(movie)):
            
            # 使用普通 image 即可，並加上相對定位讓標題可以浮動
            with ui.image(movie['poster_url']).classes('w-full aspect-[2/3]'):
                # 底部標題 (利用 NiceGUI image 的內建容器)
                ui.label(movie['title']).classes('absolute bottom-0 w-full p-2 text-white bg-black/70 text-center text-sm font-bold truncate')
            
            with ui.row().classes('p-3 justify-between items-center w-full'):
                ui.label(f"{movie['year'] or 'N/A'}").classes('text-xs text-gray-400')
                ui.badge(movie['extension'].replace('.','').upper()).props('color=blue-9')

    def play_video(self, movie):
        # The 'id' of the movie is required to build the stream URL.
        if not movie.get('id'):
            ui.notify('錯誤：找不到影片 ID，無法播放。', type='negative')
            return

        # Base URL for the stream
        base_stream_url = f"{API_BASE_URL}/stream/{movie['id']}"

        with ui.dialog() as dialog, ui.card().classes('w-[1000px] max-w-none bg-black p-0 overflow-hidden'):
            with ui.row().classes('w-full bg-gray-900 px-4 py-2 items-center justify-between'):
                ui.label(f"正在播放: {movie['title']}").classes('text-white font-medium')
                ui.button(icon='close', on_click=dialog.close).props('flat text-color=white')

            # We use a custom HTML video element to have better control over seeking
            video_id = f"video_{movie['id'].replace('-', '_')}"
            ui.html(f'''
                <video id="{video_id}" controls autoplay class="w-full aspect-video">
                    <source src="{base_stream_url}?ss=0" type="video/mp4">
                    Your browser does not support the video tag.
                </video>
            ''', sanitize=False).classes('w-full')

            # Inject the seeking logic via run_javascript
            ui.run_javascript(f'''
                const video = document.getElementById("{video_id}");
                if (video) {{
                    let isReloading = false;
                    video.onseeking = function() {{
                        if (isReloading) return;
                        
                        const currentTime = video.currentTime;
                        let isBuffered = false;
                        for (let i = 0; i < video.buffered.length; i++) {{
                            if (currentTime >= video.buffered.start(i) && currentTime <= video.buffered.end(i)) {{
                                isBuffered = true;
                                break;
                            }}
                        }}

                        if (!isBuffered) {{
                            isReloading = true;
                            video.src = "{base_stream_url}?ss=" + currentTime;
                            video.load();
                            video.play();
                            setTimeout(() => {{ isReloading = false; }}, 500);
                        }}
                    }};
                }}
            ''')

            with ui.row().classes('p-4 text-gray-500 text-xs gap-4 items-center'):
                ui.label(f"格式: {movie['extension']}")
                ui.label(f"大小: {int(movie.get('file_size', 0))/(1024*1024):.1f} MB")
                ui.link('用瀏覽器直接開啟串流', base_stream_url, new_tab=True).classes('text-blue-400 underline')
        dialog.open()

# --- 啟動與佈局 ---
ui_logic = CineWallUI()

# 全域樣式 (Figma 風格基礎)
ui.query('body').style('background-color: #121212; color: #ffffff;')

with ui.header().classes('bg-[#1a1a1a] border-b border-gray-800 items-center justify-between px-8 py-4'):
    with ui.row().classes('items-center gap-4'):
        ui.icon('theaters', size='32px').classes('text-blue-500')
        ui.label('CineWall Cloud').classes('text-2xl font-black tracking-tight')
    
    with ui.row().classes('gap-3'):
        ui.button('掃描雲端影庫', icon='refresh', on_click=ui_logic.fetch_movies).props('rounded unelevated color=blue-7')

# 主內容區
with ui.column().classes('w-full'):
    ui_logic.render_wall()

# 啟動 NiceGUI
ui.run(title='CineWall Cloud', port=8080, reload=True, dark=True)
