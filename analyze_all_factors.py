import json
import os
from PIL import Image
import numpy as np
from datetime import datetime
import matplotlib.pyplot as plt
from pathlib import Path
from typing import Dict, List, Tuple

def load_metadata() -> List[Dict]:
    """メタデータを読み込む"""
    with open('satellite_metadata.json', 'r') as f:
        return json.load(f)

def analyze_image(img: np.ndarray) -> Dict:
    """画像の統計情報を計算"""
    # RGBチャンネルごとに分析
    r, g, b = img[:, :, 0], img[:, :, 1], img[:, :, 2]
    
    # 基本統計
    stats = {
        'mean': np.mean(img),
        'std': np.std(img),
        'min': np.min(img),
        'max': np.max(img),
        'r_mean': np.mean(r),
        'g_mean': np.mean(g),
        'b_mean': np.mean(b),
        'r_std': np.std(r),
        'g_std': np.std(g),
        'b_std': np.std(b)
    }
    
    # ヒストグラムの計算
    hist, bins = np.histogram(img.flatten(), bins=256, range=(0, 256))
    stats['histogram'] = hist.tolist()
    
    # 画像の明るさ分布の特徴
    stats['brightness_range'] = stats['max'] - stats['min']
    stats['high_brightness_ratio'] = np.sum(img > 200) / img.size
    stats['low_brightness_ratio'] = np.sum(img < 50) / img.size
    
    # エッジ検出（画像のシャープさ）
    from scipy.ndimage import gaussian_filter, sobel
    img_gray = np.mean(img, axis=2)
    img_smooth = gaussian_filter(img_gray, sigma=1)
    edge = sobel(img_smooth)
    stats['edge_intensity'] = np.mean(edge)
    
    return stats

def analyze_all_factors(metadata: List[Dict], stats_list: List[Dict]) -> Dict:
    """全ての要因を分析"""
    analysis_results = {
        'time_series': {},
        'seasonal': {},
        'weather': {},
        'geographical': {}
    }
    
    # 時間系列の分析
    for meta, stats in zip(metadata, stats_list):
        date = datetime.strptime(meta['datetime'], '%Y-%m-%dT%H:%M:%SZ')
        platform = meta['platform']
        
        # 時間系列
        if platform not in analysis_results['time_series']:
            analysis_results['time_series'][platform] = []
        analysis_results['time_series'][platform].append({
            'date': date,
            'stats': stats
        })
        
        # シーズン
        month = date.month
        if month not in analysis_results['seasonal']:
            analysis_results['seasonal'][month] = []
        analysis_results['seasonal'][month].append(stats)
        
        # 天候条件（雲量が利用可能なら）
        if meta['cloud_cover'] is not None:
            cloud_cover = meta['cloud_cover']
            if cloud_cover not in analysis_results['weather']:
                analysis_results['weather'][cloud_cover] = []
            analysis_results['weather'][cloud_cover].append(stats)
        
        # 地理的位置
        lat = float(meta['bbox'][1]) + (float(meta['bbox'][3]) - float(meta['bbox'][1])) / 2
        lon = float(meta['bbox'][0]) + (float(meta['bbox'][2]) - float(meta['bbox'][0])) / 2
        if (lat, lon) not in analysis_results['geographical']:
            analysis_results['geographical'][(lat, lon)] = []
        analysis_results['geographical'][(lat, lon)].append(stats)
    
    return analysis_results

def plot_analysis(results: Dict, output_dir: str):
    """分析結果をプロット"""
    os.makedirs(output_dir, exist_ok=True)
    
    # 時間系列の可視化
    plt.figure(figsize=(12, 6))
    for platform, data in results['time_series'].items():
        dates = [d['date'] for d in data]
        means = [d['stats']['mean'] for d in data]
        plt.plot(dates, means, label=platform)
    plt.title('Brightness Over Time')
    plt.xlabel('Date')
    plt.ylabel('Mean Brightness')
    plt.legend()
    plt.savefig(f"{output_dir}/time_series.png")
    plt.close()
    
    # シーズン別の可視化
    plt.figure(figsize=(12, 6))
    months = list(range(1, 13))
    means = [np.mean([s['mean'] for s in results['seasonal'].get(m, [])]) for m in months]
    plt.bar(months, means)
    plt.title('Seasonal Brightness Pattern')
    plt.xlabel('Month')
    plt.ylabel('Mean Brightness')
    plt.xticks(months)
    plt.savefig(f"{output_dir}/seasonal.png")
    plt.close()

def main():
    # メタデータの読み込み
    metadata = load_metadata()
    
    # 画像の読み込みと分析
    stats_list = []
    for meta in metadata:
        img_path = f"satellite_images/satellite_{meta['datetime'][:10]}.png"
        if not os.path.exists(img_path):
            continue
            
        img = np.array(Image.open(img_path))
        stats = analyze_image(img)
        stats_list.append(stats)
    
    # 全ての要因の分析
    analysis_results = analyze_all_factors(metadata, stats_list)
    
    # 結果の保存と可視化
    os.makedirs('analysis_all_factors', exist_ok=True)
    plot_analysis(analysis_results, 'analysis_all_factors')
    
    # 統計の要約を保存
    time_series_stats = {}
    for platform, data in analysis_results['time_series'].items():
        if data:  # データが存在する場合のみ計算
            time_series_stats[platform] = {
                'mean_brightness': float(np.mean([d['stats']['mean'] for d in data])),
                'std_brightness': float(np.std([d['stats']['mean'] for d in data])),
                'brightness_range': float(np.mean([d['stats']['brightness_range'] for d in data]))
            }
    
    seasonal_stats = {}
    for month, data in analysis_results['seasonal'].items():
        if data:
            seasonal_stats[month] = {
                'mean_brightness': float(np.mean([s['mean'] for s in data])),
                'std_brightness': float(np.std([s['mean'] for s in data]))
            }
    
    with open('analysis_all_factors/summary.json', 'w') as f:
        json.dump({
            'time_series_stats': time_series_stats,
            'seasonal_stats': seasonal_stats
        }, f, indent=2)

if __name__ == '__main__':
    main()
