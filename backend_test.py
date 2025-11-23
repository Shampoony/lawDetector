#!/usr/bin/env python3
"""
LawAssistant Backend API Testing Suite
Tests all API endpoints for contract analysis functionality
"""

import requests
import sys
import json
import os
import tempfile
from datetime import datetime
from pathlib import Path

class LawAssistantAPITester:
    def __init__(self, base_url="https://contract-check-2.preview.emergentagent.com"):
        self.base_url = base_url
        self.api_url = f"{base_url}/api"
        self.tests_run = 0
        self.tests_passed = 0
        self.test_results = []

    def log_test(self, name, success, details=""):
        """Log test result"""
        self.tests_run += 1
        if success:
            self.tests_passed += 1
            print(f"✅ {name} - PASSED")
        else:
            print(f"❌ {name} - FAILED: {details}")
        
        self.test_results.append({
            "test": name,
            "success": success,
            "details": details,
            "timestamp": datetime.now().isoformat()
        })

    def test_api_root(self):
        """Test API root endpoint"""
        try:
            response = requests.get(f"{self.api_url}/", timeout=10)
            success = response.status_code == 200
            details = f"Status: {response.status_code}"
            if success:
                data = response.json()
                details += f", Response: {data}"
            self.log_test("API Root Endpoint", success, details)
            return success
        except Exception as e:
            self.log_test("API Root Endpoint", False, str(e))
            return False

    def test_keywords_get(self):
        """Test GET /keywords endpoint"""
        try:
            response = requests.get(f"{self.api_url}/keywords", timeout=10)
            success = response.status_code == 200
            details = f"Status: {response.status_code}"
            if success:
                keywords = response.json()
                details += f", Keywords count: {len(keywords)}"
            self.log_test("GET Keywords", success, details)
            return success, response.json() if success else []
        except Exception as e:
            self.log_test("GET Keywords", False, str(e))
            return False, []

    def test_keywords_post(self):
        """Test POST /keywords endpoint"""
        test_keyword = f"тестовое_слово_{datetime.now().strftime('%H%M%S')}"
        try:
            response = requests.post(
                f"{self.api_url}/keywords",
                json={"keyword": test_keyword},
                timeout=10
            )
            success = response.status_code == 200
            details = f"Status: {response.status_code}"
            keyword_id = None
            if success:
                data = response.json()
                keyword_id = data.get('id')
                details += f", Created keyword ID: {keyword_id}"
            self.log_test("POST Keywords", success, details)
            return success, keyword_id
        except Exception as e:
            self.log_test("POST Keywords", False, str(e))
            return False, None

    def test_keywords_delete(self, keyword_id):
        """Test DELETE /keywords/{id} endpoint"""
        if not keyword_id:
            self.log_test("DELETE Keywords", False, "No keyword ID provided")
            return False
        
        try:
            response = requests.delete(f"{self.api_url}/keywords/{keyword_id}", timeout=10)
            success = response.status_code == 200
            details = f"Status: {response.status_code}"
            if success:
                data = response.json()
                details += f", Response: {data}"
            self.log_test("DELETE Keywords", success, details)
            return success
        except Exception as e:
            self.log_test("DELETE Keywords", False, str(e))
            return False

    def create_test_file(self, content, filename, file_type="txt"):
        """Create a temporary test file"""
        temp_dir = tempfile.gettempdir()
        if file_type == "txt":
            filepath = os.path.join(temp_dir, f"{filename}.txt")
            with open(filepath, 'w', encoding='utf-8') as f:
                f.write(content)
        return filepath

    def test_analyze_contract(self):
        """Test POST /analyze endpoint with a sample contract"""
        # Create a sample Russian contract text
        sample_contract = """
        ДОГОВОР ОКАЗАНИЯ УСЛУГ №123

        Предмет договора: Оказание консультационных услуг
        
        Стоимость: 100,000 рублей
        
        Срок: до 31 декабря 2025 года
        
        Ответственность сторон:
        - Исполнитель несет полную материальную ответственность за качество услуг
        - При нарушении сроков применяется штраф в размере 10% от стоимости
        - Заказчик имеет право на одностороннее расторжение договора
        
        Порядок разрешения споров: Все споры решаются в арбитражном суде
        
        Реквизиты сторон:
        ООО "Тест" ИНН 1234567890
        ИП Иванов И.И. ИНН 0987654321
        """
        
        try:
            # Create temporary file
            filepath = self.create_test_file(sample_contract, "test_contract", "txt")
            
            with open(filepath, 'rb') as f:
                files = {'file': ('test_contract.txt', f, 'text/plain')}
                response = requests.post(
                    f"{self.api_url}/analyze",
                    files=files,
                    timeout=30  # Longer timeout for AI analysis
                )
            
            # Clean up
            os.unlink(filepath)
            
            success = response.status_code == 200
            details = f"Status: {response.status_code}"
            analysis_id = None
            
            if success:
                data = response.json()
                analysis_id = data.get('id')
                risk_level = data.get('risk_level')
                dangerous_count = len(data.get('dangerous_phrases', []))
                missing_count = len(data.get('missing_sections', []))
                has_ai_analysis = bool(data.get('ai_analysis'))
                
                details += f", Analysis ID: {analysis_id}, Risk: {risk_level}, Dangerous phrases: {dangerous_count}, Missing sections: {missing_count}, AI analysis: {has_ai_analysis}"
            else:
                try:
                    error_data = response.json()
                    details += f", Error: {error_data}"
                except:
                    details += f", Response: {response.text[:200]}"
            
            self.log_test("POST Analyze Contract", success, details)
            return success, analysis_id
            
        except Exception as e:
            self.log_test("POST Analyze Contract", False, str(e))
            return False, None

    def test_report_downloads(self, analysis_id):
        """Test report download endpoints"""
        if not analysis_id:
            self.log_test("Download JSON Report", False, "No analysis ID provided")
            self.log_test("Download HTML Report", False, "No analysis ID provided")
            return False, False
        
        # Test JSON report download
        json_success = False
        try:
            response = requests.get(f"{self.api_url}/report/{analysis_id}/json", timeout=10)
            json_success = response.status_code == 200
            details = f"Status: {response.status_code}"
            if json_success:
                details += f", Content-Type: {response.headers.get('content-type', 'unknown')}"
                details += f", Size: {len(response.content)} bytes"
            self.log_test("Download JSON Report", json_success, details)
        except Exception as e:
            self.log_test("Download JSON Report", False, str(e))
        
        # Test HTML report download
        html_success = False
        try:
            response = requests.get(f"{self.api_url}/report/{analysis_id}/html", timeout=10)
            html_success = response.status_code == 200
            details = f"Status: {response.status_code}"
            if html_success:
                details += f", Content-Type: {response.headers.get('content-type', 'unknown')}"
                details += f", Size: {len(response.content)} bytes"
            self.log_test("Download HTML Report", html_success, details)
        except Exception as e:
            self.log_test("Download HTML Report", False, str(e))
        
        return json_success, html_success

    def test_analysis_history(self):
        """Test GET /history endpoint"""
        try:
            response = requests.get(f"{self.api_url}/history", timeout=10)
            success = response.status_code == 200
            details = f"Status: {response.status_code}"
            if success:
                history = response.json()
                details += f", History count: {len(history)}"
                if history:
                    latest = history[0]
                    details += f", Latest: {latest.get('filename', 'unknown')}"
            self.log_test("GET Analysis History", success, details)
            return success
        except Exception as e:
            self.log_test("GET Analysis History", False, str(e))
            return False

    def test_file_format_validation(self):
        """Test file format validation"""
        # Test unsupported file format
        try:
            temp_dir = tempfile.gettempdir()
            filepath = os.path.join(temp_dir, "test.xyz")
            with open(filepath, 'w') as f:
                f.write("test content")
            
            with open(filepath, 'rb') as f:
                files = {'file': ('test.xyz', f, 'application/octet-stream')}
                response = requests.post(
                    f"{self.api_url}/analyze",
                    files=files,
                    timeout=10
                )
            
            os.unlink(filepath)
            
            # Should return 400 for unsupported format
            success = response.status_code == 400
            details = f"Status: {response.status_code}"
            if response.status_code == 400:
                try:
                    error_data = response.json()
                    details += f", Error: {error_data.get('detail', 'unknown')}"
                except:
                    pass
            
            self.log_test("File Format Validation", success, details)
            return success
            
        except Exception as e:
            self.log_test("File Format Validation", False, str(e))
            return False

    def run_all_tests(self):
        """Run complete test suite"""
        print("🚀 Starting LawAssistant Backend API Tests")
        print(f"📍 Testing API at: {self.api_url}")
        print("=" * 60)
        
        # Test API availability
        if not self.test_api_root():
            print("❌ API is not accessible. Stopping tests.")
            return False
        
        # Test keywords management
        print("\n📝 Testing Keywords Management...")
        keywords_get_success, existing_keywords = self.test_keywords_get()
        keywords_post_success, new_keyword_id = self.test_keywords_post()
        keywords_delete_success = self.test_keywords_delete(new_keyword_id)
        
        # Test contract analysis
        print("\n🔍 Testing Contract Analysis...")
        analyze_success, analysis_id = self.test_analyze_contract()
        
        # Test report downloads
        print("\n📄 Testing Report Downloads...")
        json_success, html_success = self.test_report_downloads(analysis_id)
        
        # Test history
        print("\n📚 Testing Analysis History...")
        history_success = self.test_analysis_history()
        
        # Test file validation
        print("\n🛡️ Testing File Validation...")
        validation_success = self.test_file_format_validation()
        
        # Print summary
        print("\n" + "=" * 60)
        print(f"📊 Test Results: {self.tests_passed}/{self.tests_run} passed")
        
        if self.tests_passed == self.tests_run:
            print("🎉 All tests passed!")
            return True
        else:
            print("⚠️ Some tests failed. Check details above.")
            return False

def main():
    """Main test execution"""
    tester = LawAssistantAPITester()
    success = tester.run_all_tests()
    
    # Save detailed results
    results_file = "/app/test_reports/backend_api_results.json"
    with open(results_file, 'w', encoding='utf-8') as f:
        json.dump({
            "timestamp": datetime.now().isoformat(),
            "total_tests": tester.tests_run,
            "passed_tests": tester.tests_passed,
            "success_rate": f"{(tester.tests_passed/tester.tests_run*100):.1f}%" if tester.tests_run > 0 else "0%",
            "test_details": tester.test_results
        }, f, indent=2, ensure_ascii=False)
    
    print(f"\n📋 Detailed results saved to: {results_file}")
    
    return 0 if success else 1

if __name__ == "__main__":
    sys.exit(main())