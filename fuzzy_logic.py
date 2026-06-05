"""
FUZZY LOGIC SYSTEM untuk TRASH BIN MONITORING
Menggabungkan: Volume, Berat, Gas CO2 untuk keputusan notifikasi

Author: Skripsi AI Detection
Date: 2026
"""

import numpy as np
from enum import Enum
from dataclasses import dataclass
from typing import Tuple, Dict, List
import json
from datetime import datetime

# ====== ENUM OUTPUT STATUS ======
class NotificationLevel(Enum):
    LOW = "LOW"           # Sampah masih aman
    MEDIUM = "MEDIUM"     # Perlu diperhatikan
    HIGH = "HIGH"         # Segera dikosongkan
    CRITICAL = "CRITICAL" # Kondisi berbahaya

@dataclass
class SensorInput:
    """Data input dari sensor"""
    volume: float        # 0-100 %
    weight: float        # kg
    co2: float           # ppm

@dataclass
class FuzzyOutput:
    """Output fuzzy logic"""
    notification_level: NotificationLevel
    confidence: float    # 0-1
    reason: str
    recommended_action: str
    timestamp: str

# ====== MEMBERSHIP FUNCTION ======
class MembershipFunction:
    """Kelas untuk menghitung membership value"""
    
    @staticmethod
    def triangular(x: float, a: float, b: float, c: float) -> float:
        """
        Fungsi membership triangular
        a=kiri, b=tengah, c=kanan
        """
        if x <= a or x >= c:
            return 0.0
        elif a < x <= b:
            return (x - a) / (b - a)
        else:
            return (c - x) / (c - b)
    
    @staticmethod
    def trapezoidal(x: float, a: float, b: float, c: float, d: float) -> float:
        """
        Fungsi membership trapezoidal
        a=kiri1, b=kiri2, c=kanan1, d=kanan2
        """
        if x <= a or x >= d:
            return 0.0
        elif a < x <= b:
            return (x - a) / (b - a)
        elif b <= x <= c:
            return 1.0
        else:
            return (d - x) / (d - c)

# ====== FUZZY INPUT SETS ======
class FuzzyVolume:
    """Fuzzifikasi untuk Volume Sampah (0-100%)"""
    
    @staticmethod
    def kosong(volume: float) -> float:
        """Volume kosong (0-30%)"""
        return MembershipFunction.trapezoidal(volume, -10, 0, 15, 30)
    
    @staticmethod
    def setengah(volume: float) -> float:
        """Volume setengah (30-70%)"""
        return MembershipFunction.triangular(volume, 30, 50, 70)
    
    @staticmethod
    def penuh(volume: float) -> float:
        """Volume penuh (70-100%)"""
        return MembershipFunction.trapezoidal(volume, 70, 80, 100, 110)

class FuzzyWeight:
    """Fuzzifikasi untuk Berat Sampah (Max: 5kg)"""
    
    @staticmethod
    def ringan(weight: float) -> float:
        """Berat ringan (0-1.5 kg)"""
        return MembershipFunction.trapezoidal(weight, -1, 0, 0.8, 1.5)
    
    @staticmethod
    def sedang(weight: float) -> float:
        """Berat sedang (1.5-3.5 kg)"""
        return MembershipFunction.triangular(weight, 1.5, 2.5, 3.5)
    
    @staticmethod
    def berat(weight: float) -> float:
        """Berat berat (3.5-5 kg)"""
        return MembershipFunction.trapezoidal(weight, 3.5, 4, 5, 5.1)

class FuzzyGas:
    """Fuzzifikasi untuk Gas CO2 (ppm)"""
    
    @staticmethod
    def normal(co2: float) -> float:
        """Gas normal (0-400 ppm)"""
        return MembershipFunction.trapezoidal(co2, -100, 0, 300, 400)
    
    @staticmethod
    def tinggi(co2: float) -> float:
        """Gas tinggi (400-600 ppm)"""
        return MembershipFunction.triangular(co2, 400, 500, 600)
    
    @staticmethod
    def bahaya(co2: float) -> float:
        """Gas bahaya (600+ ppm)"""
        return MembershipFunction.trapezoidal(co2, 600, 700, 2000, 2001)

class FuzzyOutput:
    """Output fuzzy sets untuk notification level"""
    
    @staticmethod
    def low_output(x: float) -> float:
        """Output LOW (0-25)"""
        return MembershipFunction.trapezoidal(x, -10, 0, 15, 25)
    
    @staticmethod
    def medium_output(x: float) -> float:
        """Output MEDIUM (25-50)"""
        return MembershipFunction.triangular(x, 25, 37.5, 50)
    
    @staticmethod
    def high_output(x: float) -> float:
        """Output HIGH (50-75)"""
        return MembershipFunction.triangular(x, 50, 62.5, 75)
    
    @staticmethod
    def critical_output(x: float) -> float:
        """Output CRITICAL (75-100)"""
        return MembershipFunction.trapezoidal(x, 75, 85, 100, 101)

# ====== FUZZY RULES ENGINE ======
class FuzzyRuleEngine:
    """Engine untuk processing fuzzy rules"""
    
    def __init__(self):
        self.rules = self._initialize_rules()
    
    def _initialize_rules(self) -> List[Dict]:
        """
        Inisialisasi 27 fuzzy rules
        Format: IF (volume AND weight AND gas) THEN output
        """
        rules = [
            # ============ RULE GROUP 1: KONDISI AMAN (LOW) ============
            # Rule 1: Volume kosong + Berat ringan + Gas normal
            {"volume": "kosong", "weight": "ringan", "gas": "normal", "output": "low", "priority": 1},
            
            # Rule 2: Volume kosong + Berat sedang + Gas normal
            {"volume": "kosong", "weight": "sedang", "gas": "normal", "output": "low", "priority": 1},
            
            # Rule 3: Volume setengah + Berat ringan + Gas normal
            {"volume": "setengah", "weight": "ringan", "gas": "normal", "output": "low", "priority": 1},
            
            # ============ RULE GROUP 2: KONDISI NORMAL (MEDIUM) ============
            # Rule 4: Volume setengah + Berat sedang + Gas normal
            {"volume": "setengah", "weight": "sedang", "gas": "normal", "output": "medium", "priority": 2},
            
            # Rule 5: Volume setengah + Berat berat + Gas normal
            {"volume": "setengah", "weight": "berat", "gas": "normal", "output": "medium", "priority": 2},
            
            # Rule 6: Volume penuh + Berat ringan + Gas normal
            {"volume": "penuh", "weight": "ringan", "gas": "normal", "output": "medium", "priority": 2},
            
            # Rule 7: Volume kosong + Berat ringan + Gas tinggi
            {"volume": "kosong", "weight": "ringan", "gas": "tinggi", "output": "medium", "priority": 2},
            
            # Rule 8: Volume kosong + Berat sedang + Gas tinggi
            {"volume": "kosong", "weight": "sedang", "gas": "tinggi", "output": "medium", "priority": 2},
            
            # ============ RULE GROUP 3: KONDISI PERLU PERHATIAN (HIGH) ============
            # Rule 9: Volume penuh + Berat sedang + Gas normal
            {"volume": "penuh", "weight": "sedang", "gas": "normal", "output": "high", "priority": 3},
            
            # Rule 10: Volume penuh + Berat berat + Gas normal
            {"volume": "penuh", "weight": "berat", "gas": "normal", "output": "high", "priority": 3},
            
            # Rule 11: Volume setengah + Berat ringan + Gas tinggi
            {"volume": "setengah", "weight": "ringan", "gas": "tinggi", "output": "high", "priority": 3},
            
            # Rule 12: Volume setengah + Berat sedang + Gas tinggi
            {"volume": "setengah", "weight": "sedang", "gas": "tinggi", "output": "high", "priority": 3},
            
            # Rule 13: Volume setengah + Berat berat + Gas tinggi
            {"volume": "setengah", "weight": "berat", "gas": "tinggi", "output": "high", "priority": 3},
            
            # Rule 14: Volume kosong + Berat berat + Gas normal
            {"volume": "kosong", "weight": "berat", "gas": "normal", "output": "high", "priority": 3},
            
            # Rule 15: Volume penuh + Berat ringan + Gas tinggi
            {"volume": "penuh", "weight": "ringan", "gas": "tinggi", "output": "high", "priority": 3},
            
            # Rule 16: Volume kosong + Berat ringan + Gas bahaya
            {"volume": "kosong", "weight": "ringan", "gas": "bahaya", "output": "high", "priority": 3},
            
            # ============ RULE GROUP 4: KONDISI BERBAHAYA (CRITICAL) ============
            # Rule 17: Volume penuh + Berat sedang + Gas tinggi
            {"volume": "penuh", "weight": "sedang", "gas": "tinggi", "output": "critical", "priority": 4},
            
            # Rule 18: Volume penuh + Berat berat + Gas tinggi
            {"volume": "penuh", "weight": "berat", "gas": "tinggi", "output": "critical", "priority": 4},
            
            # Rule 19: Volume penuh + Berat berat + Gas normal (volume penuh + berat) = berbahaya
            {"volume": "penuh", "weight": "berat", "gas": "normal", "output": "critical", "priority": 4},
            
            # Rule 20: ANY + ANY + Gas bahaya (prioritas tinggi)
            {"volume": "kosong", "weight": "sedang", "gas": "bahaya", "output": "critical", "priority": 4},
            
            # Rule 21: ANY + ANY + Gas bahaya
            {"volume": "kosong", "weight": "berat", "gas": "bahaya", "output": "critical", "priority": 4},
            
            # Rule 22: ANY + ANY + Gas bahaya
            {"volume": "setengah", "weight": "ringan", "gas": "bahaya", "output": "critical", "priority": 4},
            
            # Rule 23: ANY + ANY + Gas bahaya
            {"volume": "setengah", "weight": "sedang", "gas": "bahaya", "output": "critical", "priority": 4},
            
            # Rule 24: ANY + ANY + Gas bahaya
            {"volume": "setengah", "weight": "berat", "gas": "bahaya", "output": "critical", "priority": 4},
            
            # Rule 25: ANY + ANY + Gas bahaya
            {"volume": "penuh", "weight": "ringan", "gas": "bahaya", "output": "critical", "priority": 4},
            
            # Rule 26: ANY + ANY + Gas bahaya
            {"volume": "penuh", "weight": "sedang", "gas": "bahaya", "output": "critical", "priority": 4},
            
            # Rule 27: ANY + ANY + Gas bahaya (PALING BERBAHAYA)
            {"volume": "penuh", "weight": "berat", "gas": "bahaya", "output": "critical", "priority": 4},
        ]
        return rules
    
    def get_fuzzy_values(self, sensor_input: SensorInput) -> Dict:
        """Hitung membership value untuk semua fuzzy sets"""
        return {
            # Volume
            "volume_kosong": FuzzyVolume.kosong(sensor_input.volume),
            "volume_setengah": FuzzyVolume.setengah(sensor_input.volume),
            "volume_penuh": FuzzyVolume.penuh(sensor_input.volume),
            
            # Weight
            "weight_ringan": FuzzyWeight.ringan(sensor_input.weight),
            "weight_sedang": FuzzyWeight.sedang(sensor_input.weight),
            "weight_berat": FuzzyWeight.berat(sensor_input.weight),
            
            # Gas
            "gas_normal": FuzzyGas.normal(sensor_input.co2),
            "gas_tinggi": FuzzyGas.tinggi(sensor_input.co2),
            "gas_bahaya": FuzzyGas.bahaya(sensor_input.co2),
        }
    
    def evaluate_rule(self, rule: Dict, fuzzy_values: Dict) -> Tuple[str, float]:
        """Evaluasi satu rule dan kembalikan output + membership value"""
        # Ambil membership value untuk setiap kondisi
        volume_val = fuzzy_values[f"volume_{rule['volume']}"]
        weight_val = fuzzy_values[f"weight_{rule['weight']}"]
        gas_val = fuzzy_values[f"gas_{rule['gas']}"]
        
        # AND operation (min)
        rule_strength = min(volume_val, weight_val, gas_val)
        
        return rule['output'], rule_strength
    
    def process(self, sensor_input: SensorInput) -> FuzzyOutput:
        """Process sensor input dengan fuzzy logic"""
        fuzzy_values = self.get_fuzzy_values(sensor_input)
        
        # Evaluasi semua rules
        rule_results = {}
        for output_type in ["low", "medium", "high", "critical"]:
            rule_results[output_type] = []
        
        for rule in self.rules:
            output_type, strength = self.evaluate_rule(rule, fuzzy_values)
            rule_results[output_type].append(strength)
        
        # Hitung aggregate membership untuk setiap output (MAX operation)
        aggregated = {
            "low": max(rule_results["low"]) if rule_results["low"] else 0,
            "medium": max(rule_results["medium"]) if rule_results["medium"] else 0,
            "high": max(rule_results["high"]) if rule_results["high"] else 0,
            "critical": max(rule_results["critical"]) if rule_results["critical"] else 0,
        }
        
        # Defuzzifikasi menggunakan COG (Center of Gravity)
        notification_score = self._defuzzify(aggregated)
        
        # Tentukan output level berdasarkan score
        if aggregated["critical"] > 0.3:
            level = NotificationLevel.CRITICAL
            confidence = aggregated["critical"]
        elif aggregated["high"] > 0.3:
            level = NotificationLevel.HIGH
            confidence = aggregated["high"]
        elif aggregated["medium"] > 0.3:
            level = NotificationLevel.MEDIUM
            confidence = aggregated["medium"]
        else:
            level = NotificationLevel.LOW
            confidence = aggregated["low"]
        
        # Generate reasoning dan action
        reason = self._generate_reason(sensor_input, fuzzy_values)
        action = self._generate_action(level, sensor_input)
        
        return FuzzyOutput(
            notification_level=level,
            confidence=float(confidence),
            reason=reason,
            recommended_action=action,
            timestamp=datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        )
    
    def _defuzzify(self, aggregated: Dict) -> float:
        """Defuzzifikasi menggunakan Centroid method"""
        # Hitung center of gravity untuk setiap output
        cog_values = [
            15 * aggregated["low"],      # LOW center = 15
            37.5 * aggregated["medium"], # MEDIUM center = 37.5
            62.5 * aggregated["high"],   # HIGH center = 62.5
            85 * aggregated["critical"]  # CRITICAL center = 85
        ]
        
        total_weight = sum(aggregated.values())
        if total_weight == 0:
            return 0.0
        
        return sum(cog_values) / total_weight
    
    def _generate_reason(self, sensor_input: SensorInput, fuzzy_values: Dict) -> str:
        """Generate penjelasan alasan notifikasi"""
        reasons = []
        
        # Check volume
        if fuzzy_values["volume_penuh"] > 0.5:
            reasons.append("Volume sampah PENUH")
        elif fuzzy_values["volume_setengah"] > 0.5:
            reasons.append("Volume sampah setengah")
        
        # Check weight
        if fuzzy_values["weight_berat"] > 0.5:
            reasons.append("Berat sampah BERAT")
        elif fuzzy_values["weight_sedang"] > 0.5:
            reasons.append("Berat sampah sedang")
        
        # Check gas
        if fuzzy_values["gas_bahaya"] > 0.3:
            reasons.append(f"Gas CO2 BERBAHAYA ({sensor_input.co2:.0f} ppm)")
        elif fuzzy_values["gas_tinggi"] > 0.3:
            reasons.append(f"Gas CO2 tinggi ({sensor_input.co2:.0f} ppm)")
        
        return " | ".join(reasons) if reasons else "Kondisi normal"
    
    def _generate_action(self, level: NotificationLevel, sensor_input: SensorInput) -> str:
        """Generate rekomendasi aksi berdasarkan level"""
        actions = {
            NotificationLevel.LOW: "✓ Tidak ada aksi diperlukan. Lanjutkan monitoring.",
            NotificationLevel.MEDIUM: "⚠️  Perhatikan kondisi sampah. Siapkan untuk pembersihan dalam 12 jam.",
            NotificationLevel.HIGH: "🔴 SEGERA KOSONGKAN sampah untuk mencegah masalah kebersihan.",
            NotificationLevel.CRITICAL: "🚨 KONDISI BERBAHAYA! Kosongkan sampah SEKARANG dan ventilasi area. Jika gas masih tinggi, hubungi petugas."
        }
        return actions[level]

# ====== NOTIFIKASI MANAGER ======
class NotificationManager:
    """Manager untuk mengelola dan mencatat notifikasi"""
    
    def __init__(self, max_history: int = 100):
        self.history: List[Dict] = []
        self.max_history = max_history
        self.last_alert_time = {}
    
    def log_notification(self, box_id: int, fuzzy_output: FuzzyOutput, sensor_data: SensorInput):
        """Catat notifikasi ke history"""
        record = {
            "box_id": box_id,
            "timestamp": fuzzy_output.timestamp,
            "level": fuzzy_output.notification_level.value,
            "confidence": fuzzy_output.confidence,
            "reason": fuzzy_output.reason,
            "action": fuzzy_output.recommended_action,
            "sensor_data": {
                "volume": round(sensor_data.volume, 2),
                "weight": round(sensor_data.weight, 2),
                "co2": round(sensor_data.co2, 2)
            }
        }
        
        self.history.append(record)
        
        # Maintain max history
        if len(self.history) > self.max_history:
            self.history.pop(0)
        
        return record
    
    def get_history(self, box_id: int = None) -> List[Dict]:
        """Ambil history notifikasi"""
        if box_id is None:
            return self.history
        return [h for h in self.history if h["box_id"] == box_id]
    
    def get_latest_status(self, box_id: int) -> Dict:
        """Ambil status terbaru box tertentu"""
        records = self.get_history(box_id)
        if records:
            return records[-1]
        return None
    
    def export_to_json(self, filename: str = "trash_notifications.json"):
        """Export history ke JSON"""
        with open(filename, 'w') as f:
            json.dump(self.history, f, indent=2)
        print(f"✓ Exported {len(self.history)} records to {filename}")

# ====== MAIN SYSTEM ======
class FuzzyTrashSystem:
    """Main system yang mengintegrasikan fuzzy logic untuk 3 bin sampah"""
    
    def __init__(self):
        self.rule_engine = FuzzyRuleEngine()
        self.notification_manager = NotificationManager()
        self.box_status = {
            1: {"name": "PLASTIK", "last_level": None},
            2: {"name": "KERTAS", "last_level": None},
            3: {"name": "LOGAM", "last_level": None}
        }
    
    def process_box(self, box_id: int, sensor_data: SensorInput) -> FuzzyOutput:
        """Process satu box sampah"""
        fuzzy_output = self.rule_engine.process(sensor_data)
        
        # Log notifikasi
        self.notification_manager.log_notification(box_id, fuzzy_output, sensor_data)
        
        # Update status
        self.box_status[box_id]["last_level"] = fuzzy_output.notification_level.value
        
        return fuzzy_output
    
    def process_all_boxes(self, sensor_data_list: List[SensorInput]) -> Dict:
        """Process semua 3 box sekaligus"""
        results = {}
        for box_id, sensor_data in enumerate(sensor_data_list, 1):
            results[box_id] = self.process_box(box_id, sensor_data)
        return results
    
    def get_system_status(self) -> Dict:
        """Ambil status keseluruhan sistem"""
        return {
            "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "boxes": self.box_status,
            "history_count": len(self.notification_manager.history)
        }
    
    def get_alert_summary(self) -> Dict:
        """Ambil ringkasan alert"""
        alert_counts = {"LOW": 0, "MEDIUM": 0, "HIGH": 0, "CRITICAL": 0}
        
        for record in self.notification_manager.history[-50:]:  # Last 50 records
            alert_counts[record["level"]] += 1
        
        return alert_counts

# ====== TESTING FUNCTION ======
def test_fuzzy_system():
    """Test fuzzy system dengan berbagai skenario"""
    print("="*70)
    print("   FUZZY LOGIC TRASH BIN NOTIFICATION SYSTEM - TEST")
    print("="*70)
    
    system = FuzzyTrashSystem()
    
    # Test Case 1: Kondisi Aman
    print("\n[TEST 1] Kondisi AMAN - Volume 20%, Berat 0.5kg, Gas 350ppm")
    sensor1 = SensorInput(volume=20, weight=0.5, co2=350)
    output1 = system.process_box(1, sensor1)
    print_output(1, sensor1, output1)
    
    # Test Case 2: Kondisi Normal
    print("\n[TEST 2] Kondisi NORMAL - Volume 50%, Berat 3kg, Gas 400ppm")
    sensor2 = SensorInput(volume=50, weight=3, co2=400)
    output2 = system.process_box(2, sensor2)
    print_output(2, sensor2, output2)
    
    # Test Case 3: Perlu Perhatian
    print("\n[TEST 3] PERLU PERHATIAN - Volume 80%, Berat 5kg, Gas 450ppm")
    sensor3 = SensorInput(volume=80, weight=5, co2=450)
    output3 = system.process_box(3, sensor3)
    print_output(3, sensor3, output3)
    
    # Test Case 4: Berbahaya
    print("\n[TEST 4] BERBAHAYA - Volume 95%, Berat 5kg, Gas 700ppm")
    sensor4 = SensorInput(volume=95, weight=5, co2=700)
    output4 = system.process_box(1, sensor4)
    print_output(1, sensor4, output4)
    
    # Test Case 5: Gas Sangat Tinggi
    print("\n[TEST 5] GAS SANGAT TINGGI - Volume 30%, Berat 4.5kg, Gas 900ppm")
    sensor5 = SensorInput(volume=30, weight=4.5, co2=900)
    output5 = system.process_box(2, sensor5)
    print_output(2, sensor5, output5)
    
    # System Summary
    print("\n" + "="*70)
    print("   SYSTEM STATUS SUMMARY")
    print("="*70)
    status = system.get_system_status()
    print(f"Timestamp: {status['timestamp']}")
    print(f"Total Notifications Logged: {status['history_count']}")
    print(f"\nAlert Summary (Last 50 records):")
    summary = system.get_alert_summary()
    for level, count in summary.items():
        print(f"  {level}: {count}")

def print_output(box_id: int, sensor: SensorInput, output: FuzzyOutput):
    """Print formatted output"""
    print(f"\n  📦 BOX {box_id}")
    print(f"  ─────────────────────────────────────────")
    print(f"  Input Sensor:")
    print(f"    • Volume: {sensor.volume:.1f}%")
    print(f"    • Berat:  {sensor.weight:.2f} kg")
    print(f"    • CO2:    {sensor.co2:.0f} ppm")
    print(f"  ")
    print(f"  Output Fuzzy Logic:")
    print(f"    • Level: {output.notification_level.value} (Confidence: {output.confidence:.2%})")
    print(f"    • Reason: {output.reason}")
    print(f"    • Action: {output.recommended_action}")

if __name__ == "__main__":
    test_fuzzy_system()
