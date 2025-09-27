#!/usr/bin/env python3
"""
Test script to verify iOS project structure and configuration.
Ensures the regenerated Xcode project is properly configured.
"""

import os
import xml.etree.ElementTree as ET
from pathlib import Path


class TestiOSProjectStructure:
    """Test iOS project structure and configuration."""
    
    def __init__(self):
        self.ios_root = Path("ios")
        self.project_path = self.ios_root / "CalendarEventApp.xcodeproj"
        self.main_app_path = self.ios_root / "CalendarEventApp"
        self.extension_path = self.ios_root / "CalendarEventExtension"
    
    def test_project_structure(self):
        """Test that all required project files exist."""
        print("Testing iOS project structure...")
        
        required_files = [
            # Project files
            self.project_path / "project.pbxproj",
            self.project_path / "project.xcworkspace" / "contents.xcworkspacedata",
            self.project_path / "xcshareddata" / "xcschemes" / "CalendarEventApp.xcscheme",
            
            # Main app files
            self.main_app_path / "CalendarEventApp.swift",
            self.main_app_path / "ContentView.swift",
            self.main_app_path / "EventResultView.swift",
            self.main_app_path / "ApiService.swift",
            self.main_app_path / "Models.swift",
            self.main_app_path / "Info.plist",
            
            # Extension files
            self.extension_path / "ActionViewController.swift",
            self.extension_path / "ApiService.swift",
            self.extension_path / "Info.plist",
            self.extension_path / "MainInterface.storyboard",
        ]
        
        missing_files = []
        for file_path in required_files:
            if not file_path.exists():
                missing_files.append(str(file_path))
            else:
                print(f"✓ Found: {file_path}")
        
        if missing_files:
            print(f"✗ Missing files: {missing_files}")
            return False
        
        print("✓ All required files found")
        return True
    
    def test_project_pbxproj(self):
        """Test that project.pbxproj has correct structure."""
        print("\nTesting project.pbxproj structure...")
        
        pbxproj_path = self.project_path / "project.pbxproj"
        
        try:
            with open(pbxproj_path, 'r') as f:
                content = f.read()
            
            # Check for required sections
            required_sections = [
                "PBXBuildFile section",
                "PBXFileReference section",
                "PBXFrameworksBuildPhase section",
                "PBXGroup section",
                "PBXNativeTarget section",
                "PBXProject section",
                "PBXSourcesBuildPhase section",
                "XCBuildConfiguration section",
                "XCConfigurationList section"
            ]
            
            missing_sections = []
            for section in required_sections:
                if section not in content:
                    missing_sections.append(section)
                else:
                    print(f"✓ Found: {section}")
            
            if missing_sections:
                print(f"✗ Missing sections: {missing_sections}")
                return False
            
            # Check for target names
            if "CalendarEventApp" not in content:
                print("✗ Missing CalendarEventApp target")
                return False
            
            if "CalendarEventExtension" not in content:
                print("✗ Missing CalendarEventExtension target")
                return False
            
            print("✓ project.pbxproj structure is valid")
            return True
            
        except Exception as e:
            print(f"✗ Error reading project.pbxproj: {e}")
            return False
    
    def test_info_plist_files(self):
        """Test that Info.plist files are valid XML."""
        print("\nTesting Info.plist files...")
        
        plist_files = [
            self.main_app_path / "Info.plist",
            self.extension_path / "Info.plist"
        ]
        
        for plist_path in plist_files:
            try:
                tree = ET.parse(plist_path)
                root = tree.getroot()
                
                if root.tag != "plist":
                    print(f"✗ Invalid plist root tag in {plist_path}")
                    return False
                
                print(f"✓ Valid plist: {plist_path}")
                
            except ET.ParseError as e:
                print(f"✗ XML parse error in {plist_path}: {e}")
                return False
            except Exception as e:
                print(f"✗ Error reading {plist_path}: {e}")
                return False
        
        return True
    
    def test_bundle_identifiers(self):
        """Test that bundle identifiers are correctly configured."""
        print("\nTesting bundle identifiers...")
        
        try:
            # Check main app Info.plist
            main_plist = self.main_app_path / "Info.plist"
            tree = ET.parse(main_plist)
            
            # Check extension Info.plist
            ext_plist = self.extension_path / "Info.plist"
            tree = ET.parse(ext_plist)
            
            # Check project.pbxproj for bundle identifiers
            pbxproj_path = self.project_path / "project.pbxproj"
            with open(pbxproj_path, 'r') as f:
                content = f.read()
            
            if "com.jacolabs.CalendarEventApp" not in content:
                print("✗ Main app bundle identifier not found in project")
                return False
            
            if "com.jacolabs.CalendarEventApp.CalendarEventExtension" not in content:
                print("✗ Extension bundle identifier not found in project")
                return False
            
            print("✓ Bundle identifiers are correctly configured")
            return True
            
        except Exception as e:
            print(f"✗ Error checking bundle identifiers: {e}")
            return False
    
    def test_swift_files(self):
        """Test that Swift files have valid syntax (basic check)."""
        print("\nTesting Swift files...")
        
        swift_files = [
            self.main_app_path / "CalendarEventApp.swift",
            self.main_app_path / "ContentView.swift",
            self.main_app_path / "EventResultView.swift",
            self.main_app_path / "ApiService.swift",
            self.main_app_path / "Models.swift",
            self.extension_path / "ActionViewController.swift",
            self.extension_path / "ApiService.swift",
        ]
        
        for swift_file in swift_files:
            try:
                with open(swift_file, 'r') as f:
                    content = f.read()
                
                # Basic syntax checks
                if not content.strip():
                    print(f"✗ Empty Swift file: {swift_file}")
                    return False
                
                if "import" not in content:
                    print(f"✗ No imports found in: {swift_file}")
                    return False
                
                print(f"✓ Valid Swift file: {swift_file}")
                
            except Exception as e:
                print(f"✗ Error reading {swift_file}: {e}")
                return False
        
        return True
    
    def test_workspace_configuration(self):
        """Test workspace configuration files."""
        print("\nTesting workspace configuration...")
        
        workspace_files = [
            self.project_path / "project.xcworkspace" / "contents.xcworkspacedata",
            self.project_path / "project.xcworkspace" / "xcshareddata" / "IDEWorkspaceChecks.plist"
        ]
        
        for workspace_file in workspace_files:
            try:
                if workspace_file.suffix == '.plist':
                    tree = ET.parse(workspace_file)
                    print(f"✓ Valid workspace plist: {workspace_file}")
                else:
                    tree = ET.parse(workspace_file)
                    print(f"✓ Valid workspace XML: {workspace_file}")
                    
            except ET.ParseError as e:
                print(f"✗ XML parse error in {workspace_file}: {e}")
                return False
            except Exception as e:
                print(f"✗ Error reading {workspace_file}: {e}")
                return False
        
        return True
    
    def test_scheme_configuration(self):
        """Test scheme configuration."""
        print("\nTesting scheme configuration...")
        
        scheme_path = self.project_path / "xcshareddata" / "xcschemes" / "CalendarEventApp.xcscheme"
        
        try:
            tree = ET.parse(scheme_path)
            root = tree.getroot()
            
            if root.tag != "Scheme":
                print(f"✗ Invalid scheme root tag")
                return False
            
            # Check for required elements
            if not root.find(".//BuildAction"):
                print("✗ Missing BuildAction in scheme")
                return False
            
            if not root.find(".//LaunchAction"):
                print("✗ Missing LaunchAction in scheme")
                return False
            
            print("✓ Scheme configuration is valid")
            return True
            
        except Exception as e:
            print(f"✗ Error reading scheme: {e}")
            return False
    
    def run_all_tests(self):
        """Run all tests and provide summary."""
        print("iOS Project Structure Validation")
        print("=" * 50)
        
        tests = [
            ("Project Structure", self.test_project_structure),
            ("Project.pbxproj", self.test_project_pbxproj),
            ("Info.plist Files", self.test_info_plist_files),
            ("Bundle Identifiers", self.test_bundle_identifiers),
            ("Swift Files", self.test_swift_files),
            ("Workspace Configuration", self.test_workspace_configuration),
            ("Scheme Configuration", self.test_scheme_configuration),
        ]
        
        passed = 0
        failed = 0
        
        for test_name, test_func in tests:
            try:
                if test_func():
                    passed += 1
                else:
                    failed += 1
            except Exception as e:
                print(f"✗ {test_name} FAILED with exception: {e}")
                failed += 1
        
        print(f"\n{'='*50}")
        print(f"Test Results: {passed} passed, {failed} failed")
        
        if failed == 0:
            print("\n🎉 All iOS project structure tests passed!")
            print("\nThe iOS project is ready:")
            print("• Clean Xcode project structure")
            print("• Valid project.pbxproj configuration")
            print("• Proper Info.plist files for both targets")
            print("• Correct bundle identifiers")
            print("• Valid Swift source files")
            print("• Proper workspace and scheme configuration")
            print("\n📱 You can now open the project in Xcode!")
            return True
        else:
            print(f"\n❌ {failed} test(s) failed. Please fix the issues above.")
            return False


if __name__ == "__main__":
    test = TestiOSProjectStructure()
    success = test.run_all_tests()
    exit(0 if success else 1)