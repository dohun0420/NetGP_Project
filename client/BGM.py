from pico2d import load_music


class BGM:
    # 배경음악 전용 클래스. 그리기와 상관없이 화면(상태)이 바뀔 때 play() / stop() 을 부른다.
    #   예) 플레이 화면 : Bgm('Cave.mp3'),  상점 : Bgm('Store.mp3')   (기존 Map / Store 와 같은 파일 · 볼륨 32)
    def __init__(self, filename, volume=32):
        self.music = load_music(filename)
        self.music.set_volume(volume)

    def play(self):
        self.music.repeat_play()

    def stop(self):
        self.music.stop()