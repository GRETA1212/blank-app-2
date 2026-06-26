from app.main import Scene, normalized_durations, seconds_to_srt


def test_srt_timestamp():
    assert seconds_to_srt(65.432) == "00:01:05,432"


def test_scene_durations_sum_to_audio():
    scenes = [Scene(scene_number=1, duration_seconds=1), Scene(scene_number=2, duration_seconds=3)]
    values = normalized_durations(scenes, 40.0)
    assert round(sum(values), 5) == 40.0
    assert values[1] > values[0]
