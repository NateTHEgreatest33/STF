#*********************************************************************
#
#   MODULE NAME:
#       results.py - results handler class
#
#   DESCRIPTION:
#       Provides results collection and file generation
#
#   Copyright 2025 by Nate Lenze
#*********************************************************************

#---------------------------------------------------------------------
#                              IMPORTS
#---------------------------------------------------------------------
import os
import git
from datetime import datetime


#---------------------------------------------------------------------
#                          HELPER CLASSES
#---------------------------------------------------------------------
class consoleColor:
    HEADER = '\033[95m'
    OKBLUE = '\033[94m'
    OKCYAN = '\033[96m'
    OKGREEN = '\033[92m'
    WARNING = '\033[93m'
    FAIL = '\033[91m'
    ENDC = '\033[0m'
    BOLD = '\033[1m'
    UNDERLINE = '\033[4m'

#---------------------------------------------------------------------
#                             CLASSES
#---------------------------------------------------------------------
class results:
    # ================================
    # local variables
    # ================================
    __text_replacement = [ ( "\r",               "\\r" ),
                           ( "\n",               "\\n" ),
                           ( "\x1b[2J\x1b[0;0H", "[clear screen]" ) ]

    # ================================
    # results constructor
    # ================================
    def __init__(self, fut ):
        self.file_under_test = fut
        self.date_time       = datetime.now()
        self.checksum        = ( git.Repo(search_parent_directories=True) ).head.object.hexsha
        self.test_case_list  = []
        self.req_list        = []

    # ================================
    # results deconstructor
    # ================================
    def __del__(self):
        self.__publish_results()

    # ================================
    # requirement
    # ================================
    def test_requirement( self, req ):
        self.req_list.append( req )
        print( consoleColor.HEADER + "Req Tested > "+ req )
    # ================================
    # test step
    # ================================
    def test_step( self, step ):
         self.__global_compare( True, "step", 0, 0, step )
    # ================================
    # compare equal
    # ================================
    def compare_equal( self, expected, actual, case ):
        cmp = expected == actual
        self.__global_compare( cmp, "==", expected, actual, case )

    # ================================
    # compare not equal 
    # ================================ 
    def compare_not_equal( self, expected, actual, case ):
        cmp = expected != actual
        self.__global_compare( cmp, "!=", expected, actual, case )

    # ================================
    # compare less than
    # ================================ 
    def compare_less_than( self, expected, actual, case ):
        cmp = expected < actual
        self.__global_compare( cmp, "<", expected, actual, case )

    # ================================
    # compare more than
    # ================================
    def compare_more_than( self, expected, actual, case ):
        cmp = expected > actual
        self.__global_compare( cmp, ">", expected, actual, case )

    # ================================
    # global compare function
    # ================================
    def __global_compare( self, result, cmp_type, x, y, case ):
        self.test_case_list.append( [result, cmp_type, x, y, case ] )
        self.__console( result, cmp_type, x, y, case )
    
    def __console( self, result, cmp_type, x, y, case ):
        if cmp_type == "step":
            print( consoleColor.HEADER + case )
            return
        print( consoleColor.ENDC + case + ": " + self.__text_cleanser(x) + " " + cmp_type + " " + self.__text_cleanser(y) )
        color = consoleColor.OKGREEN if result is True else consoleColor.FAIL
        print( color + str(result) )

    # ================================
    # text cleanser
    # ================================
    def __text_cleanser( self, item ):
        text = str(item)
        
        for orginal, replace in self.__text_replacement:
            text = text.replace( orginal, replace ) 
	
        return text


    # ================================
    # publish results
    # ================================
    def __publish_results( self ):
        # ============================
        # initailize global pass/fail
        # to true to start test
        # ============================
        pass_fail = True

        # ============================
        # format & open results file
        # ============================
        results_file = self.file_under_test[:-3] + "_results.html"
        f = open(results_file, "w")

        # ============================
        # add general header info (as a small table)
        # ============================
        f.write("<!DOCTYPE html>\n")
        f.write("<html>\n")
        f.write("<head>\n")
        f.write("<title>Test Results</title>\n")
        f.write("<style>\n")
        f.write("  body { font-family: Arial, sans-serif; color: #333; line-height: 1.4; }\n")
        f.write("  .container { width: 80%; margin: 0 auto; padding: 20px; border: 1px solid #ccc; border-radius: 10px; }\n")
        f.write("  h1 { text-align: center; color: #444; margin-bottom: 20px; }\n")
        f.write("  h2 { color: #555; border-bottom: 1px solid #eee; padding-bottom: 5px; margin-top: 20px; }\n")
        f.write("  .info-table { width: 100%; border-collapse: collapse; margin-bottom: 15px; font-size: 0.9em; }\n")
        f.write("  .info-table td { border: 1px solid #eee; padding: 5px; text-align: left; }\n")
        f.write("  .info-table td:first-child { font-weight: bold; width: 150px; }\n")
        f.write("  .test-case-block { border: 1px solid #ddd; margin-bottom: 10px; padding: 10px; border-radius: 5px; }\n")
        f.write("  .test-case-header { display: flex; justify-content: space-between; align-items: center; margin-bottom: 5px; }\n")
        f.write("  .test-case-header h4 { margin: 0; color: #666; }\n")
        f.write("  .status-pass { color: white; background-color: green; padding: 3px 8px; border-radius: 3px; font-size: 0.9em; }\n")
        f.write("  .status-fail { color: white; background-color: red; padding: 3px 8px; border-radius: 3px; font-size: 0.9em; }\n")
        f.write("  .details { padding-left: 15px; display: none; font-size: 0.9em; }\n")
        f.write("  .detail { margin-bottom: 3px; }\n")
        f.write("  .step-block { border: 1px solid #eee; margin-bottom: 8px; padding: 8px; border-radius: 5px; background-color: #f8f8f8; display: flex; justify-content: space-between; align-items: center; }\n")
        f.write("  .step-tag { color: #555; font-style: italic; font-size: 0.9em; background-color: #ffdd57; padding: 3px 6px; border-radius: 3px; }\n")
        f.write("  .overall-pass { color: white; background-color: green; padding: 10px; border-radius: 5px; text-align: center; margin-top: 20px; font-weight: bold; }\n")
        f.write("  .overall-fail { color: white; background-color: red; padding: 10px; border-radius: 5px; text-align: center; margin-top: 20px; font-weight: bold; }\n")
        f.write("</style>\n")
        f.write("</head>\n")
        f.write("<body>\n")
        f.write("<div class='container'>\n")  # Start container div

        f.write("<h1>{}  Results</h1>\n".format(self.file_under_test[:-3]))
        f.write("<table class='info-table'>\n")
        f.write("  <tr><td>File Under Test:</td><td>{}</td></tr>\n".format(os.path.basename(self.file_under_test)))
        f.write("  <tr><td>Current Test:</td><td>{}</td></tr>\n".format(os.path.basename(results_file)))
        f.write("  <tr><td>FUT sha:</td><td>{}</td></tr>\n".format(self.checksum))
        f.write("  <tr><td>Date:</td><td>{}</td></tr>\n".format(self.date_time.ctime()))
        f.write("</table>\n")

        f.write("<h2>Requirements Tested</h2>\n")
        if self.req_list:
            f.write("<ul>\n")
            for req in self.req_list:
                f.write("  <li>{}</li>\n".format(req))
            f.write("</ul>\n")
        else:
            f.write("<p>No requirements tested.</p>\n")

        # ============================
        # run through test-cases (as collapsible blocks with status)
        # ============================
        f.write("<h2>Test Cases</h2>\n")
        for index, [result, cmp_type, x, y, case ] in enumerate(self.test_case_list):
            # =========================
            # Special handling for step's
            # =========================
            if cmp_type == "step":
                f.write(f"<div class='step-block'><span>{case}</span><!--<span class='step-tag'>Step</span>--></div>\n")
                continue

            # =========================
            # normal handling (as collapsible blocks with status)
            # =========================
            pass_fail = pass_fail and result
            status_class = "status-pass" if result else "status-fail"
            status_text = "Pass" if result else "Fail"
            block_id = f"test-case-{index}"
            f.write(f"<div class='test-case-block' onclick=\"toggleDetails('{block_id}')\">\n")
            f.write(f"  <div class='test-case-header'>\n")
            # f.write(f"    <h4>Test Case: {case}</h4>\n")
            f.write(f"    <h4>{case}</h4>\n")
            f.write(f"    <span class='{status_class}'>{status_text}</span>\n")
            f.write("  </div>\n")
            f.write(f"  <div id='{block_id}' class='details'>\n")
            f.write(f"    <p class='detail'><b>Comparison:</b> {cmp_type}</p>\n")
            f.write(f"    <p class='detail'><b>Expected:</b> {self.__text_cleanser(x)}</p>\n")
            f.write(f"    <p class='detail'><b>Actual:</b> {self.__text_cleanser(y)}</p>\n")
            f.write("  </div>\n")
            f.write("</div>\n")

        # ============================
        # Print overal result to file (at the end)
        # ============================
        f.write("<h2>Overall Result</h2>\n")
        overall_result_class = "overall-pass" if pass_fail else "overall-fail"
        f.write("<p class='{}'>Overall Test Result: {}</p>\n".format(overall_result_class, "Pass" if pass_fail else "Fail"))

        # ============================
        # Print overal result to console
        # ============================
        print( consoleColor.ENDC + "\nOverall Result: ")
        color = consoleColor.OKGREEN if pass_fail is True else consoleColor.FAIL
        print( color + str(pass_fail) )

        # ============================
        # Add JavaScript for toggling details
        # ============================
        f.write("<script>\n")
        f.write("function toggleDetails(id) {\n")
        f.write("  var details = document.getElementById(id);\n")
        f.write("  if (details.style.display === 'none') {\n")
        f.write("    details.style.display = 'block';\n")
        f.write("  } else {\n")
        f.write("    details.style.display = 'none';\n")
        f.write("  }\n")
        f.write("}\n")
        f.write("</script>\n")

        # ============================
        # close file
        # ============================
        f.write("</div>\n")  # Close container div
        f.write("</body>\n")
        f.write("</html>\n")
        f.close()