#!/usr/bin/env python
# -*- coding: utf-8 -*-
import rospy
import rospkg
from std_msgs.msg import String
from sound_system.srv import *
import json
import os
import re
import time


class Nlp:
    def __init__(self):
        rospy.init_node("nlp_main")

        # json操作用変数定義
        self.nlp_dic = self.make_nlp_dic(rospy.get_param("json_name"))
        self.recog_dic = {}
        self.command_list = []
        self.speak_text = ""
        self.dic_name = ""

        # 現在の発話内容と辞書名を格納するための変数
        self.previous_speak_text = ""
        self.previous_dic_name = ""

        # 関数の引数
        self.argument = ""

        rospy.Subscriber("/natural_language_processing/speak_sentence", String, self.speak_sentence_callback)
        rospy.Subscriber("/sound_system/result", String, self.speech_recognition_callback)


    def speak_sentence_callback(self, data):
        # type: (String) -> None
        """
        競技のパッケージから発話内容を受け取る
        :param data:発話内容
        :return: なし
        """
        self.speak_text = data.data
        self.previous_speak_text = self.speak_text
        self.decide_variable()  # 発話内容から各変数の値を決定
        self.start_recognition(self.dic_name)  # 音声認識開始


    def speech_recognition_callback(self, data):
        # type: (String) -> None
        """
        sound_system_ros から音声認識結果を受け取る関数
        :param data:音声認識結果
        :return: なし
        """
        text = self.text_modify(data.data)

        # 発話をもう一度繰り返す
        if text == "please say again":
            self.speak(self.previous_speak_text)
            self.start_recognition(self.previous_dic_name)
        else:
            # textがyes/noなら関数呼び出し
            if text == "yes" or text == "no":
                if self.recog_dic[text] != "":
                    function = self.recog_dic[text]
                    function_argument_pub = rospy.Publisher("/natural_language_processing/{}".format(function),
                                                            String, queue_size=10)
                    time.sleep(1)
                    function_argument_pub.publish(self.argument)
                    self.argument = ""  # 引数を初期化
                # 関数がなければ再び音声認識を開始
                else:
                    self.speak("OK.")
                    self.decide_variable()
                    self.start_recognition(self.dic_name)

            # textがyes/no以外ならyes/no判定へ
            else:
                match_flag = False
                for sentence in self.recog_dic:
                    #  正規表現とtextがマッチするとき
                    if re.search(sentence, text) is not None:
                        self.argument = re.sub(sentence, "", text)
                        match_flag = True
                        self.recog_dic = self.recog_dic[sentence]
                        self.speak("You said {}. Am I correct? Please answer yes or no.".format(text))
                        self.start_recognition("yes_no_sphinx")
                        break
                # 誤認識のためもう一度音声認識開始
                if not match_flag:
                    self.start_recognition(self.dic_name)


    def decide_variable(self):
        # type: () -> None
        """
        発話内容から各変数を決定する.
        :return: なし
        """
        self.command_list = self.nlp_dic[self.speak_text]
        self.dic_name = self.command_list[0]  # 音声認識の辞書名
        self.recog_dic = self.command_list[1]  # キーは音声認識結果、値は辞書型変数か関数名


    def start_recognition(self, param):
        # type: (str) -> None
        """
        1.sound_system_ros に対して音声認識を要求する
        2.辞書名を変数に格納しておく
        :param param: sphinxの辞書名
        :return: なし
        """
        rospy.wait_for_service("/sound_system/recognition")
        rospy.ServiceProxy("/sound_system/recognition", StringService)(param)
        self.previous_dic_name = param


    def speak(self, text):
        # type: (str) -> None
        """
        1.sound_system_ros に対して発話を要求する
          発話が終了するまで待機
        2.発話内容を変数に格納しておく
        :param text: 発話内容
        :return: なし
        """
        rospy.wait_for_service("/sound_system/speak")
        rospy.ServiceProxy("/sound_system/speak", StringService)(text)
        self.previous_speak_text = text


    @staticmethod
    def make_nlp_dic(json_name):
        # type: (str) -> dict
        """
        処理の流れが記述してあるjsonファイルを読み込み
        以下の辞書型へと変換する.
        key:発話内容(string)
        value:[音声認識辞書(string), {key:左記の音声認識結果, value:{yes/noをkeyとする辞書}]
        :param: jsonファイル名
        :return: 辞書型変数
        """
        json_path = "{}/{}".format(rospkg.RosPack().get_path("natural_language_processing"), "etc/nlp_json")
        json_file = open(os.path.join(json_path, json_name), 'r')
        return json.load(json_file)


    @staticmethod
    def text_modify(text):
        # type: (str) -> str
        """
        与えられた文字列 に以下の処理を加える
        1. 文字列内のアンダースコア( _ ) をすべて半角スペースに変換
        2. 文字列内のアルファベットをすべて小文字化
        :param text: 処理する文字列
        :return: 処理後の文字列
        """
        if text is not None:
            text = text.replace("_", " ")
            text = text.lower()

        return text


if __name__ == "__main__":
    Nlp()
    rospy.spin()