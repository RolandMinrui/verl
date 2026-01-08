from pydantic import BaseModel, Field
from typing import Dict, List, Optional, Any
from mcp.server.fastmcp import FastMCP
import os
import uuid
import math

# Section 1: Schema
class AudioTimeSeries(BaseModel):
    """Represents audio time series data."""
    id: str = Field(..., description="Unique identifier for the audio time series")
    file_path: str = Field(..., description="Original file path")
    sample_rate: int = Field(default=22050, ge=1, description="Sample rate in Hz")
    samples: List[float] = Field(default_factory=list, description="Audio samples")
    duration: float = Field(default=0.0, ge=0, description="Duration in seconds")

class DownloadedFile(BaseModel):
    """Represents a downloaded audio file."""
    url: str = Field(..., description="Source URL")
    file_path: str = Field(..., description="Local file path")

class ChromaData(BaseModel):
    """Represents chroma CQT data."""
    id: str = Field(..., description="Unique identifier")
    audio_id: str = Field(..., description="Reference to audio time series")
    data: List[Dict[str, Any]] = Field(default_factory=list, description="Chroma data rows")

class MFCCData(BaseModel):
    """Represents MFCC data."""
    id: str = Field(..., description="Unique identifier")
    audio_id: str = Field(..., description="Reference to audio time series")
    coefficients: List[List[float]] = Field(default_factory=list, description="MFCC coefficients")

class MusicAnalysisScenario(BaseModel):
    """Main scenario model for music analysis."""
    downloaded_files: Dict[str, DownloadedFile] = Field(default_factory=dict, description="Downloaded audio files by path")
    audio_time_series: Dict[str, AudioTimeSeries] = Field(default_factory=dict, description="Loaded audio time series by path")
    chroma_data: Dict[str, ChromaData] = Field(default_factory=dict, description="Computed chroma data by path")
    mfcc_data: Dict[str, MFCCData] = Field(default_factory=dict, description="Computed MFCC data by path")
    download_directory: str = Field(default="./downloads", description="Directory for downloaded files")
    output_directory: str = Field(default="./output", description="Directory for output CSV files")
    default_sample_rate: int = Field(default=22050, ge=1, description="Default sample rate for audio loading")
    note_names: List[str] = Field(default_factory=lambda: ["C", "C#", "D", "D#", "E", "F", "F#", "G", "G#", "A", "A#", "B"], description="Chromatic scale note names")

Scenario_Schema = [AudioTimeSeries, DownloadedFile, ChromaData, MFCCData, MusicAnalysisScenario]

# Section 2: Class
class MusicAnalysisAPI:
    def __init__(self):
        """Initialize music analysis API with empty state."""
        self.downloaded_files: Dict[str, DownloadedFile] = {}
        self.audio_time_series: Dict[str, AudioTimeSeries] = {}
        self.chroma_data: Dict[str, ChromaData] = {}
        self.mfcc_data: Dict[str, MFCCData] = {}
        self.download_directory: str = "./downloads"
        self.output_directory: str = "./output"
        self.default_sample_rate: int = 22050
        self.note_names: List[str] = ["C", "C#", "D", "D#", "E", "F", "F#", "G", "G#", "A", "A#", "B"]

    def load_scenario(self, scenario: dict) -> None:
        """Load scenario data into the API instance."""
        model = MusicAnalysisScenario(**scenario)
        self.downloaded_files = {k: DownloadedFile(**v) if isinstance(v, dict) else v for k, v in model.downloaded_files.items()}
        self.audio_time_series = {k: AudioTimeSeries(**v) if isinstance(v, dict) else v for k, v in model.audio_time_series.items()}
        self.chroma_data = {k: ChromaData(**v) if isinstance(v, dict) else v for k, v in model.chroma_data.items()}
        self.mfcc_data = {k: MFCCData(**v) if isinstance(v, dict) else v for k, v in model.mfcc_data.items()}
        self.download_directory = model.download_directory
        self.output_directory = model.output_directory
        self.default_sample_rate = model.default_sample_rate
        self.note_names = model.note_names

    def save_scenario(self) -> dict:
        """Save current state as scenario dictionary."""
        return {
            "downloaded_files": {k: v.model_dump() for k, v in self.downloaded_files.items()},
            "audio_time_series": {k: v.model_dump() for k, v in self.audio_time_series.items()},
            "chroma_data": {k: v.model_dump() for k, v in self.chroma_data.items()},
            "mfcc_data": {k: v.model_dump() for k, v in self.mfcc_data.items()},
            "download_directory": self.download_directory,
            "output_directory": self.output_directory,
            "default_sample_rate": self.default_sample_rate,
            "note_names": self.note_names
        }

    def download_from_url(self, url: str) -> dict:
        """Download an audio file from a remote URL and save it locally."""
        filename = url.split("/")[-1].split("?")[0]
        if not filename:
            filename = f"audio_{uuid.uuid4().hex[:8]}"
        
        if not (filename.endswith(".mp3") or filename.endswith(".wav")):
            if ".mp3" in url.lower():
                filename += ".mp3"
            else:
                filename += ".wav"
        
        file_path = os.path.join(self.download_directory, filename)
        
        downloaded = DownloadedFile(url=url, file_path=file_path)
        self.downloaded_files[file_path] = downloaded
        
        return {"file_path": file_path}

    def load_audio_segment(self, file_path: str, offset: Optional[float] = None, duration: Optional[float] = None) -> dict:
        """Load an audio file and extract its time series data."""
        if offset is None:
            offset = 0.0
        
        audio_id = uuid.uuid4().hex
        
        base_duration = 180.0
        if duration is not None:
            actual_duration = min(duration, base_duration - offset)
        else:
            actual_duration = base_duration - offset
        
        if actual_duration < 0:
            actual_duration = 0.0
        
        num_samples = int(actual_duration * self.default_sample_rate)
        samples = []
        for i in range(min(num_samples, 1000)):
            t = (offset + i / self.default_sample_rate)
            sample = math.sin(2 * math.pi * 440 * t) * 0.5
            samples.append(sample)
        
        audio_ts = AudioTimeSeries(
            id=audio_id,
            file_path=file_path,
            sample_rate=self.default_sample_rate,
            samples=samples,
            duration=actual_duration
        )
        
        csv_filename = f"audio_ts_{audio_id}.csv"
        audio_time_series_path = os.path.join(self.output_directory, csv_filename)
        
        self.audio_time_series[audio_time_series_path] = audio_ts
        
        return {"audio_time_series_path": audio_time_series_path}

    def get_duration(self, audio_time_series_path: str) -> dict:
        """Calculate the total duration of a loaded audio time series."""
        audio_ts = self.audio_time_series[audio_time_series_path]
        return {"duration_seconds": audio_ts.duration}

    def estimate_tempo(self, audio_time_series_path: str, hop_length: Optional[int] = None,
                       start_bpm: Optional[float] = None, std_bpm: Optional[float] = None,
                       ac_size: Optional[float] = None, max_tempo: Optional[float] = None) -> dict:
        """Estimate the tempo (beats per minute) of an audio time series."""
        if hop_length is None:
            hop_length = 512
        if start_bpm is None:
            start_bpm = 120.0
        if std_bpm is None:
            std_bpm = 1.0
        if ac_size is None:
            ac_size = 8.0
        if max_tempo is None:
            max_tempo = 320.0
        
        audio_ts = self.audio_time_series[audio_time_series_path]
        
        duration = audio_ts.duration
        if duration > 0:
            estimated_beats = duration / 60.0 * start_bpm
            tempo_variation = (len(audio_ts.samples) % 40) - 20
            tempo_bpm = start_bpm + tempo_variation * std_bpm
            tempo_bpm = max(30.0, min(tempo_bpm, max_tempo))
        else:
            tempo_bpm = start_bpm
        
        return {"tempo_bpm": round(tempo_bpm, 2)}

    def chroma_cqt(self, audio_time_series_path: str, hop_length: Optional[int] = None,
                   fmin: Optional[float] = None, n_chroma: Optional[int] = None,
                   n_octaves: Optional[int] = None) -> dict:
        """Compute the chroma CQT feature."""
        if hop_length is None:
            hop_length = 512
        if n_chroma is None:
            n_chroma = 12
        if n_octaves is None:
            n_octaves = 7
        
        audio_ts = self.audio_time_series[audio_time_series_path]
        
        chroma_id = uuid.uuid4().hex
        data = []
        
        num_frames = max(1, int(audio_ts.duration * audio_ts.sample_rate / hop_length))
        num_frames = min(num_frames, 100)
        
        for frame_idx in range(num_frames):
            time_sec = frame_idx * hop_length / audio_ts.sample_rate
            for note_idx in range(min(n_chroma, len(self.note_names))):
                amplitude = abs(math.sin(frame_idx * 0.1 + note_idx * 0.5)) * 0.8 + 0.1
                data.append({
                    "note": self.note_names[note_idx],
                    "time": round(time_sec, 4),
                    "amplitude": round(amplitude, 4)
                })
        
        chroma = ChromaData(
            id=chroma_id,
            audio_id=audio_ts.id,
            data=data
        )
        
        csv_filename = f"chroma_cqt_{chroma_id}.csv"
        chroma_cqt_path = os.path.join(self.output_directory, csv_filename)
        
        self.chroma_data[chroma_cqt_path] = chroma
        
        return {"chroma_cqt_path": chroma_cqt_path}

    def mfcc(self, audio_time_series_path: str) -> dict:
        """Compute MFCC features."""
        audio_ts = self.audio_time_series[audio_time_series_path]
        
        mfcc_id = uuid.uuid4().hex
        n_mfcc = 13
        hop_length = 512
        
        num_frames = max(1, int(audio_ts.duration * audio_ts.sample_rate / hop_length))
        num_frames = min(num_frames, 100)
        
        coefficients = []
        for frame_idx in range(num_frames):
            frame_coeffs = []
            for coeff_idx in range(n_mfcc):
                value = math.cos(frame_idx * 0.05 + coeff_idx * 0.3) * (10.0 / (coeff_idx + 1))
                frame_coeffs.append(round(value, 4))
            coefficients.append(frame_coeffs)
        
        mfcc_data = MFCCData(
            id=mfcc_id,
            audio_id=audio_ts.id,
            coefficients=coefficients
        )
        
        csv_filename = f"mfcc_{mfcc_id}.csv"
        mfcc_path = os.path.join(self.output_directory, csv_filename)
        
        self.mfcc_data[mfcc_path] = mfcc_data
        
        return {"mfcc_path": mfcc_path}

    def beat_track(self, audio_time_series_path: str, hop_length: Optional[int] = None,
                   start_bpm: Optional[float] = None, tightness: Optional[int] = None,
                   units: Optional[str] = None) -> dict:
        """Detect beat locations and estimate tempo."""
        if hop_length is None:
            hop_length = 512
        if start_bpm is None:
            start_bpm = 120.0
        if tightness is None:
            tightness = 100
        if units is None:
            units = "frames"
        
        audio_ts = self.audio_time_series[audio_time_series_path]
        
        duration = audio_ts.duration
        tempo_variation = (len(audio_ts.samples) % 40) - 20
        tempo = start_bpm + tempo_variation * (100 / tightness)
        tempo = max(30.0, min(tempo, 320.0))
        
        beat_interval_seconds = 60.0 / tempo
        num_beats = int(duration / beat_interval_seconds) if duration > 0 else 0
        
        beats = []
        for i in range(num_beats):
            beat_time = i * beat_interval_seconds
            
            if units == "time":
                beats.append(round(beat_time, 4))
            elif units == "samples":
                beat_sample = int(beat_time * audio_ts.sample_rate)
                beats.append(beat_sample)
            else:
                beat_frame = int(beat_time * audio_ts.sample_rate / hop_length)
                beats.append(beat_frame)
        
        return {
            "tempo": round(tempo, 2),
            "beats": beats
        }


# Section 3: MCP Tools
mcp = FastMCP(name="MusicAnalysis")
api = MusicAnalysisAPI()

@mcp.tool()
def load_scenario(scenario: dict) -> str:
    """
    Load scenario data into the music analysis API.
    
    Args:
        scenario (dict): Scenario dictionary matching MusicAnalysisScenario schema.
    
    Returns:
        success_message (str): Success message.
    """
    try:
        if not isinstance(scenario, dict):
            raise ValueError("Scenario must be a dictionary")
        api.load_scenario(scenario)
        return "Successfully loaded scenario"
    except Exception as e:
        raise e

@mcp.tool()
def save_scenario() -> dict:
    """
    Save current music analysis state as scenario dictionary.
    
    Returns:
        scenario (dict): Dictionary containing all current state variables.
    """
    try:
        return api.save_scenario()
    except Exception as e:
        raise e

@mcp.tool()
def download_from_url(url: str) -> dict:
    """
    Download an audio file from a remote URL and save it locally for subsequent analysis.
    
    Args:
        url (str): The URL of the audio file to download. Must point to a file ending with .mp3 or .wav extension.
    
    Returns:
        file_path (str): The local file system path where the downloaded audio file has been saved.
    """
    try:
        if not url or not isinstance(url, str):
            raise ValueError("URL must be a non-empty string")
        if not (url.lower().endswith(".mp3") or url.lower().endswith(".wav") or ".mp3" in url.lower() or ".wav" in url.lower()):
            raise ValueError("URL must point to an audio file with .mp3 or .wav extension")
        return api.download_from_url(url)
    except Exception as e:
        raise e

@mcp.tool()
def load_audio_segment(file_path: str, offset: Optional[float] = None, duration: Optional[float] = None) -> dict:
    """
    Load an audio file and extract its time series data for use in subsequent analysis functions.
    
    Args:
        file_path (str): The path to the audio file to load. Can be a local file path or a path returned from download functions.
        offset (float): [Optional] The time offset in seconds from which to start reading the audio file. Defaults to 0.0 (start of file).
        duration (float): [Optional] The maximum duration in seconds to load from the audio file. If not specified, loads the entire file from the offset.
    
    Returns:
        audio_time_series_path (str): The path to a CSV file containing the extracted audio time series data, used as input for analysis functions.
    """
    try:
        if not file_path or not isinstance(file_path, str):
            raise ValueError("File path must be a non-empty string")
        if offset is not None and offset < 0:
            raise ValueError("Offset must be non-negative")
        if duration is not None and duration <= 0:
            raise ValueError("Duration must be positive")
        return api.load_audio_segment(file_path, offset, duration)
    except Exception as e:
        raise e

@mcp.tool()
def get_duration(audio_time_series_path: str) -> dict:
    """
    Calculate the total duration of a loaded audio time series.
    
    Args:
        audio_time_series_path (str): The path to a CSV file containing audio time series data, as returned by the load_audio_segment function.
    
    Returns:
        duration_seconds (float): The total duration of the audio time series in seconds.
    """
    try:
        if not audio_time_series_path or not isinstance(audio_time_series_path, str):
            raise ValueError("Audio time series path must be a non-empty string")
        if audio_time_series_path not in api.audio_time_series:
            raise ValueError(f"Audio time series not found: {audio_time_series_path}")
        return api.get_duration(audio_time_series_path)
    except Exception as e:
        raise e

@mcp.tool()
def estimate_tempo(audio_time_series_path: str, hop_length: Optional[int] = None,
                   start_bpm: Optional[float] = None, std_bpm: Optional[float] = None,
                   ac_size: Optional[float] = None, max_tempo: Optional[float] = None) -> dict:
    """
    Estimate the tempo (beats per minute) of an audio time series using autocorrelation-based analysis.
    
    Args:
        audio_time_series_path (str): The path to a CSV file containing audio time series data, as returned by the load_audio_segment function.
        hop_length (int): [Optional] The number of audio samples between successive analysis frames. Defaults to 512.
        start_bpm (float): [Optional] The initial tempo estimate in BPM used as a prior for tempo detection. Defaults to 120.
        std_bpm (float): [Optional] The standard deviation of the tempo distribution prior, controlling how tightly the estimate is constrained. Defaults to 1.0.
        ac_size (float): [Optional] The size of the autocorrelation window in seconds used for tempo estimation. Defaults to 8.0.
        max_tempo (float): [Optional] The maximum tempo in BPM that the algorithm will consider detecting. Defaults to 320.0.
    
    Returns:
        tempo_bpm (float): The estimated tempo of the audio in beats per minute (BPM).
    """
    try:
        if not audio_time_series_path or not isinstance(audio_time_series_path, str):
            raise ValueError("Audio time series path must be a non-empty string")
        if audio_time_series_path not in api.audio_time_series:
            raise ValueError(f"Audio time series not found: {audio_time_series_path}")
        if hop_length is not None and hop_length <= 0:
            raise ValueError("Hop length must be positive")
        if start_bpm is not None and start_bpm <= 0:
            raise ValueError("Start BPM must be positive")
        if max_tempo is not None and max_tempo <= 0:
            raise ValueError("Max tempo must be positive")
        return api.estimate_tempo(audio_time_series_path, hop_length, start_bpm, std_bpm, ac_size, max_tempo)
    except Exception as e:
        raise e

@mcp.tool()
def chroma_cqt(audio_time_series_path: str, hop_length: Optional[int] = None,
               fmin: Optional[float] = None, n_chroma: Optional[int] = None,
               n_octaves: Optional[int] = None) -> dict:
    """
    Compute the chroma CQT (Constant-Q Transform chromagram) feature, representing the pitch class content of the audio over time.
    
    Args:
        audio_time_series_path (str): The path to a CSV file containing audio time series data, as returned by the load_audio_segment function.
        hop_length (int): [Optional] The number of audio samples between successive analysis frames. Defaults to 512.
        fmin (float): [Optional] The minimum frequency in Hz for the chroma feature extraction. If not specified, uses a default based on the audio sample rate.
        n_chroma (int): [Optional] The number of chroma bins to compute. Defaults to 12, corresponding to the 12 notes of the chromatic scale.
        n_octaves (int): [Optional] The number of octaves to include in the chroma feature computation. Defaults to 7.
    
    Returns:
        chroma_cqt_path (str): The path to a CSV file containing the chroma CQT data with columns: note (pitch class), time (in seconds), and amplitude (energy).
    """
    try:
        if not audio_time_series_path or not isinstance(audio_time_series_path, str):
            raise ValueError("Audio time series path must be a non-empty string")
        if audio_time_series_path not in api.audio_time_series:
            raise ValueError(f"Audio time series not found: {audio_time_series_path}")
        if hop_length is not None and hop_length <= 0:
            raise ValueError("Hop length must be positive")
        if n_chroma is not None and n_chroma <= 0:
            raise ValueError("Number of chroma bins must be positive")
        if n_octaves is not None and n_octaves <= 0:
            raise ValueError("Number of octaves must be positive")
        return api.chroma_cqt(audio_time_series_path, hop_length, fmin, n_chroma, n_octaves)
    except Exception as e:
        raise e

@mcp.tool()
def mfcc(audio_time_series_path: str) -> dict:
    """
    Compute MFCC (Mel-frequency cepstral coefficients) features, representing the spectral envelope and timbral characteristics of the audio.
    
    Args:
        audio_time_series_path (str): The path to a CSV file containing audio time series data, as returned by the load_audio_segment function.
    
    Returns:
        mfcc_path (str): The path to a CSV file containing the computed MFCC coefficients over time.
    """
    try:
        if not audio_time_series_path or not isinstance(audio_time_series_path, str):
            raise ValueError("Audio time series path must be a non-empty string")
        if audio_time_series_path not in api.audio_time_series:
            raise ValueError(f"Audio time series not found: {audio_time_series_path}")
        return api.mfcc(audio_time_series_path)
    except Exception as e:
        raise e

@mcp.tool()
def beat_track(audio_time_series_path: str, hop_length: Optional[int] = None,
               start_bpm: Optional[float] = None, tightness: Optional[int] = None,
               units: Optional[str] = None) -> dict:
    """
    Detect beat locations and estimate tempo from an audio time series using dynamic programming beat tracking.
    
    Args:
        audio_time_series_path (str): The path to a CSV file containing audio time series data, as returned by the load_audio_segment function.
        hop_length (int): [Optional] The number of audio samples between successive analysis frames. Defaults to 512.
        start_bpm (float): [Optional] The initial tempo estimate in BPM used as a prior for beat tracking. Defaults to 120.
        tightness (int): [Optional] The tightness parameter controlling how strictly beats must follow the tempo estimate. Higher values enforce stricter tempo adherence. Defaults to 100.
        units (str): [Optional] The units for reporting beat locations. Valid values are 'frames' (analysis frame indices), 'samples' (audio sample indices), or 'time' (seconds). Defaults to 'frames'.
    
    Returns:
        tempo (float): The estimated tempo of the audio in beats per minute (BPM).
        beats (list): A list of detected beat locations expressed in the specified units (frames, samples, or time in seconds).
    """
    try:
        if not audio_time_series_path or not isinstance(audio_time_series_path, str):
            raise ValueError("Audio time series path must be a non-empty string")
        if audio_time_series_path not in api.audio_time_series:
            raise ValueError(f"Audio time series not found: {audio_time_series_path}")
        if hop_length is not None and hop_length <= 0:
            raise ValueError("Hop length must be positive")
        if start_bpm is not None and start_bpm <= 0:
            raise ValueError("Start BPM must be positive")
        if tightness is not None and tightness <= 0:
            raise ValueError("Tightness must be positive")
        if units is not None and units not in ["frames", "samples", "time"]:
            raise ValueError("Units must be one of: 'frames', 'samples', 'time'")
        return api.beat_track(audio_time_series_path, hop_length, start_bpm, tightness, units)
    except Exception as e:
        raise e


# Section 4: Entry Point
if __name__ == "__main__":
    mcp.run()