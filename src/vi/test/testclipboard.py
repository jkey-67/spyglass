import unittest
from vi.clipboard import evaluateClipboardJumpbridgeData, evaluateClipboardStructureData
from vi.clipboard import tokenize_eve_formatted_text, evaluateClipboardData
import random


class TestClipBoardParsers(unittest.TestCase):
    def test_evaluateClipboardJumpbridgeData(self):
        items = ['<a href="showinfo:35841//1037567076715">8CN-CH » OX-S7P - Speedway</a>',
                 '<a href="showinfo:35841//1037567076715">8CN-CH » OX-S7P - Speedway</a> in 8CN-CH',
                 'DUO-51 » L-FM3P',
                 'OX-S7P » 8CN-CH',
                 'OX-S7P » 8CN-CH - Speedway 2',
                 'OX-S7P » 8CN-CH - Speedway 2\n test 123',
                 '123445 OX-S7P --> 8CN-CH',
                 '123445 OX-S7P » 8CN-CH']
        random.shuffle(items)
        for itm in items:
            res_type, res = evaluateClipboardJumpbridgeData(itm)
            self.assertEqual(res_type, "jumpbridge", "Result of '{}'is not jumpbridge".format(itm))

        for itm in items:
            res_type, res = evaluateClipboardData(itm)
            self.assertEqual(res_type, "jumpbridge", "Result of '{}'is not jumpbridge".format(itm))

        items = ['bla', 'bla blabla', 'bla bla bla']
        random.shuffle(items)
        for itm in items:
            res_type, res = evaluateClipboardJumpbridgeData(itm)
            self.assertEqual(res_type, None, "Result of '{}'is not jumpbridge".format(itm))

    def test_evaluateClipboardPoitOfInterestData(self):
        pos_list = [
            """<a href="showinfo:35834//1045388775216">1P-WGB - C E E C E E S T A R</a>""",
            "<url=showinfo:52678//60003760 alt='Current Station'>Jita IV - Moon 4 - Caldari Navy Assembly Plant</url>",
            "<url=showinfo:1531//60002476 alt='Current Station'>Vittenyn IV - Moon 6"
            " - Expert Distribution Warehouse</url>"
        ]
        # random.shuffle(pos_list)
        for itm in pos_list:
            res_type, res = evaluateClipboardStructureData(itm)
            self.assertEqual(res_type, "poi", "Result of '{}' is not poi".format(itm))

        for itm in pos_list:
            res_type, res = evaluateClipboardData(itm)
            self.assertEqual(res_type, "poi", "Result of '{}' is not poi".format(itm))

    def test_tokenize_eve_formatted_text(self):
        res = tokenize_eve_formatted_text("""<font size="14" color="#bfffffff"></font><font size="14" color="#ffd98d00"><loc><a href="showinfo:3871//60003460">Jita IV - Moon 10 - Caldari Business Tribunal Law School</a><a href="showinfo:32880">  </a><a href="showinfo:1529//60003466">Jita IV - Moon 4 - Caldari Business Tribunal Bureau Offices</a><a href="showinfo:32880">  </a><a href="showinfo:3872//60003469">Jita IV - Caldari Business Tribunal Information Center</a><a href="showinfo:32880">  </a><a href="showinfo:3871//60003463">Jita VII - Moon 2 - Caldari Business Tribunal Law School</a><a href="showinfo:32880">  </a><a href="showinfo:1529//60002959">Jita IV - Moon 10 - Caldari Constructions Production Plant</a><a href="showinfo:32880">  </a><a href="showinfo:1529//60002953">Jita V - Moon 17 - Caldari Constructions Production Plant</a><a href="showinfo:32880">  </a><a href="showinfo:52678//60003760">Jita IV - Moon 4 - Caldari Navy Assembly Plant</a><a href="showinfo:32880">  </a><a href="showinfo:1529//60003757">Jita IV - Moon 5 - Caldari Navy Assembly Plant</a><a href="showinfo:32880">  </a><a href="showinfo:1529//60004423">Jita IV - Moon 6 - Caldari Provisions School</a><a href="showinfo:32880">  </a><a href="showinfo:1529//60003055">Jita IV - Moon 11 - Expert Housing Production Plant</a><a href="showinfo:32880">  </a><a href="showinfo:4024//60000451">Jita IV - Moon 6 - Hyasyoda Corporation Refinery</a><a href="showinfo:32880">  </a><a href="showinfo:4024//60000463">Jita VI - Hyasyoda Corporation Refinery</a><a href="showinfo:32880">  </a><a href="showinfo:71361//60015169">Jita VI - Paragon Fulfillment Center</a><a href="showinfo:32880">  </a><a href="showinfo:1531//60000361">Jita IV - Moon 6 - Ytiri Storage</a><a href="showinfo:32880">  </a><a href="showinfo:1531//60000364">Jita V - Moon 14 - Ytiri Storage</a><a href="showinfo:32880"> </a></loc></font>""")
        self.assertEqual(len(res), 1, "Len should be > 1")

        res = tokenize_eve_formatted_text("""<font size="14" color="#bfffffff"></font><font size="14" color="#ffd98d00"><a href="showinfo:35834//1045388775216">1P-WGB - C E E C E E S T A R</a></font><font size="14" color="#bfffffff">  </font><font size="14" color="#ffd98d00"><a href="showinfo:35833//1043585874292">F4R2-Q - Round X</a></font><font size="14" color="#bfffffff">  </font><font size="14" color="#ffd98d00"><a href="showinfo:35834//1044008398262">F4R2-Q - J A B R O N I S T A R</a></font><font size="14" color="#bfffffff">  </font><font size="14" color="#ffd98d00"><a href="showinfo:35833//1043422778283">WLAR-J - GONE WITH THE WIND</a></font><font size="14" color="#bfffffff">  </font><font size="14" color="#ffd98d00"><a href="showinfo:35833//1044166050180">U-QVWD - Atlas</a></font><font size="14" color="#bfffffff"> </font>""")
        self.assertEqual(len(res), 5, "Len should be > 1")

        res = tokenize_eve_formatted_text("test 123")
        self.assertEqual(len(res), 1, "Len should be > 1")