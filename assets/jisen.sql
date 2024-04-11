/*
 Navicat Premium Data Transfer

 Source Server         : localhost_3306
 Source Server Type    : MySQL
 Source Server Version : 50540
 Source Host           : localhost:3306
 Source Schema         : jisen

 Target Server Type    : MySQL
 Target Server Version : 50540
 File Encoding         : 65001

 Date: 10/04/2024 21:31:03
*/

SET NAMES utf8mb4;
SET FOREIGN_KEY_CHECKS = 0;

-- ----------------------------
-- Table structure for check_ce
-- ----------------------------
DROP TABLE IF EXISTS `check_ce`;
CREATE TABLE `check_ce`  (
  `id` int(11) NOT NULL AUTO_INCREMENT,
  `username` varchar(255) CHARACTER SET utf8 COLLATE utf8_general_ci NULL DEFAULT NULL,
  `dataline` datetime NULL DEFAULT NULL,
  `work_num` text CHARACTER SET utf8 COLLATE utf8_general_ci NULL,
  `pdf_path` text CHARACTER SET utf8 COLLATE utf8_general_ci NULL,
  `pdf_name` text CHARACTER SET utf8 COLLATE utf8_general_ci NULL,
  `excel_path` text CHARACTER SET utf8 COLLATE utf8_general_ci NULL,
  `excel_name` text CHARACTER SET utf8 COLLATE utf8_general_ci NULL,
  `work_table` text CHARACTER SET utf8 COLLATE utf8_general_ci NULL,
  `result` text CHARACTER SET utf8 COLLATE utf8_general_ci NULL,
  PRIMARY KEY (`id`) USING BTREE
) ENGINE = InnoDB AUTO_INCREMENT = 8 CHARACTER SET = utf8 COLLATE = utf8_general_ci ROW_FORMAT = Compact;

-- ----------------------------
-- Records of check_ce
-- ----------------------------
INSERT INTO `check_ce` VALUES (1, 'zhangsan', '2024-04-07 10:53:22', '006', 'D:\\PrintCmpFile\\004\\2024\\0407\\10-53-21\\zhangsan\\a.pdf', 'a.pdf', 'D:\\PrintCmpFile\\004\\2024\\0407\\10-53-21\\zhangsan\\a.xlsx', 'a.xlsx', '例2', 'D:\\PrintCmpFile\\004\\2024\\0407\\10-53-21\\zhangsan\\result');
INSERT INTO `check_ce` VALUES (2, 'zhangsan', '2024-04-07 14:56:57', '006', 'D:\\PrintCmpFile\\004\\2024\\0407\\14-56-56\\zhangsan\\checkLine.pdf', 'checkLine.pdf', 'D:\\PrintCmpFile\\004\\2024\\0407\\14-56-56\\zhangsan\\a.xlsx', 'a.xlsx', 'K113BCC3', 'D:\\PrintCmpFile\\004\\2024\\0407\\14-56-56\\zhangsan\\result');
INSERT INTO `check_ce` VALUES (3, 'zhangsan', '2024-04-07 14:59:11', '006', 'D:\\PrintCmpFile\\004\\2024\\0407\\14-59-11\\zhangsan\\checkLine.pdf', 'checkLine.pdf', 'D:\\PrintCmpFile\\004\\2024\\0407\\14-59-11\\zhangsan\\a.xlsx', 'a.xlsx', 'K113BCC3', 'D:\\PrintCmpFile\\004\\2024\\0407\\14-59-11\\zhangsan\\result');
INSERT INTO `check_ce` VALUES (4, 'zhangsan', '2024-04-07 19:31:31', '006', 'D:\\PrintCmpFile\\004\\2024\\0407\\19-31-30\\zhangsan\\a.xlsx.pdf', 'a.xlsx.pdf', 'D:\\PrintCmpFile\\004\\2024\\0407\\19-31-30\\zhangsan\\a.pdf.xlsx', 'a.pdf.xlsx', 'K113BCC3', 'D:\\PrintCmpFile\\004\\2024\\0407\\19-31-30\\zhangsan\\result');
INSERT INTO `check_ce` VALUES (5, 'zhangsan', '2024-04-08 22:56:30', '004', 'D:\\PrintCmpFile\\004\\2024\\0408\\22-56-29\\zhangsan\\a.pdf.pdf', 'a.pdf.pdf', 'D:\\PrintCmpFile\\004\\2024\\0408\\22-56-29\\zhangsan\\a.xlsx.xlsx', 'a.xlsx.xlsx', '例1', 'D:\\PrintCmpFile\\004\\2024\\0408\\22-56-29\\zhangsan\\result');
INSERT INTO `check_ce` VALUES (6, 'zhangsan', '2024-04-09 10:00:15', '004', 'D:\\PrintCmpFile\\004\\2024\\0409\\10-00-15\\zhangsan\\a.pdf', 'a.pdf', 'D:\\PrintCmpFile\\004\\2024\\0409\\10-00-15\\zhangsan\\a.xlsx', 'a.xlsx', '例1', 'D:\\PrintCmpFile\\004\\2024\\0409\\10-00-15\\zhangsan\\result');
INSERT INTO `check_ce` VALUES (7, 'zhangsan', '2024-04-09 10:06:32', '004', 'D:\\PrintCmpFile\\004\\2024\\0409\\10-06-32\\zhangsan\\a.pdf', 'a.pdf', 'D:\\PrintCmpFile\\004\\2024\\0409\\10-06-32\\zhangsan\\a.xlsx', 'a.xlsx', '例1', 'D:\\PrintCmpFile\\004\\2024\\0409\\10-06-32\\zhangsan\\result');

-- ----------------------------
-- Table structure for check_diff_pdf
-- ----------------------------
DROP TABLE IF EXISTS `check_diff_pdf`;
CREATE TABLE `check_diff_pdf`  (
  `id` int(11) NOT NULL AUTO_INCREMENT,
  `username` varchar(255) CHARACTER SET utf8 COLLATE utf8_general_ci NULL DEFAULT NULL,
  `dataline` datetime NULL DEFAULT NULL,
  `work_num` text CHARACTER SET utf8 COLLATE utf8_general_ci NULL,
  `pdf_path1` text CHARACTER SET utf8 COLLATE utf8_general_ci NULL,
  `pdf_name1` text CHARACTER SET utf8 COLLATE utf8_general_ci NULL,
  `pdf_path2` text CHARACTER SET utf8 COLLATE utf8_general_ci NULL,
  `pdf_name2` text CHARACTER SET utf8 COLLATE utf8_general_ci NULL,
  `result` text CHARACTER SET utf8 COLLATE utf8_general_ci NULL,
  `is_error` tinyint(255) NULL DEFAULT NULL,
  PRIMARY KEY (`id`) USING BTREE
) ENGINE = InnoDB AUTO_INCREMENT = 28 CHARACTER SET = utf8 COLLATE = utf8_general_ci ROW_FORMAT = Compact;

-- ----------------------------
-- Records of check_diff_pdf
-- ----------------------------
INSERT INTO `check_diff_pdf` VALUES (13, 'zhangsan', '2024-04-02 22:36:34', '006', 'D:\\PrintCmpFile\\004\\2024\\0402\\22-36-17\\zhangsan\\1.pdf', '1.pdf', 'D:\\PrintCmpFile\\004\\2024\\0402\\22-36-17\\zhangsan\\2.pdf', '2.pdf', 'D:\\PrintCmpFile\\004\\2024\\0402\\22-36-17\\zhangsan\\result', 1);
INSERT INTO `check_diff_pdf` VALUES (14, 'zhangsan', '2024-04-02 22:37:25', '006', 'D:\\PrintCmpFile\\009\\2024\\0402\\22-37-07\\zhangsan\\1.pdf', '1.pdf', 'D:\\PrintCmpFile\\009\\2024\\0402\\22-37-07\\zhangsan\\2.pdf', '2.pdf', 'D:\\PrintCmpFile\\009\\2024\\0402\\22-37-07\\zhangsan\\result', 1);
INSERT INTO `check_diff_pdf` VALUES (15, 'zhangsan', '2024-04-03 11:05:29', '006', 'D:\\PrintCmpFile\\009\\2024\\0403\\11-05-13\\zhangsan\\1.pdf', '1.pdf', 'D:\\PrintCmpFile\\009\\2024\\0403\\11-05-13\\zhangsan\\2.pdf', '2.pdf', 'D:\\PrintCmpFile\\009\\2024\\0403\\11-05-13\\zhangsan\\result', 1);
INSERT INTO `check_diff_pdf` VALUES (16, 'zhangsan', '2024-04-03 12:25:38', '006', 'D:\\PrintCmpFile\\009\\2024\\0403\\12-25-20\\zhangsan\\3.pdf', '3.pdf', 'D:\\PrintCmpFile\\009\\2024\\0403\\12-25-20\\zhangsan\\4.pdf', '4.pdf', 'D:\\PrintCmpFile\\009\\2024\\0403\\12-25-20\\zhangsan\\result', 1);
INSERT INTO `check_diff_pdf` VALUES (17, 'zhangsan', '2024-04-03 12:29:15', '006', 'D:\\PrintCmpFile\\009\\2024\\0403\\12-29-00\\zhangsan\\1.pdf', '1.pdf', 'D:\\PrintCmpFile\\009\\2024\\0403\\12-29-00\\zhangsan\\2.pdf', '2.pdf', 'D:\\PrintCmpFile\\009\\2024\\0403\\12-29-00\\zhangsan\\result', 1);
INSERT INTO `check_diff_pdf` VALUES (18, 'zhangsan', '2024-04-03 12:30:39', '006', 'D:\\PrintCmpFile\\009\\2024\\0403\\12-30-25\\zhangsan\\1.pdf', '1.pdf', 'D:\\PrintCmpFile\\009\\2024\\0403\\12-30-25\\zhangsan\\2.pdf', '2.pdf', 'D:\\PrintCmpFile\\009\\2024\\0403\\12-30-25\\zhangsan\\result', 1);
INSERT INTO `check_diff_pdf` VALUES (19, 'zhangsan', '2024-04-03 12:31:37', '006', 'D:\\PrintCmpFile\\009\\2024\\0403\\12-31-22\\zhangsan\\1.pdf', '1.pdf', 'D:\\PrintCmpFile\\009\\2024\\0403\\12-31-22\\zhangsan\\2.pdf', '2.pdf', 'D:\\PrintCmpFile\\009\\2024\\0403\\12-31-22\\zhangsan\\result', 1);
INSERT INTO `check_diff_pdf` VALUES (20, 'zhangsan', '2024-04-03 12:40:40', '006', 'D:\\PrintCmpFile\\009\\2024\\0403\\12-40-25\\zhangsan\\1.pdf', '1.pdf', 'D:\\PrintCmpFile\\009\\2024\\0403\\12-40-25\\zhangsan\\2.pdf', '2.pdf', 'D:\\PrintCmpFile\\009\\2024\\0403\\12-40-25\\zhangsan\\result', 1);
INSERT INTO `check_diff_pdf` VALUES (21, 'zhangsan', '2024-04-03 14:46:24', '006', 'D:\\PrintCmpFile\\009\\2024\\0403\\14-46-09\\zhangsan\\1.pdf', '1.pdf', 'D:\\PrintCmpFile\\009\\2024\\0403\\14-46-09\\zhangsan\\2.pdf', '2.pdf', 'D:\\PrintCmpFile\\009\\2024\\0403\\14-46-09\\zhangsan\\result', 1);
INSERT INTO `check_diff_pdf` VALUES (22, 'zhangsan', '2024-04-03 16:21:23', '006', 'D:\\PrintCmpFile\\001\\2024\\0403\\16-21-22\\zhangsan\\1.pdf', '1.pdf', 'D:\\PrintCmpFile\\001\\2024\\0403\\16-21-22\\zhangsan\\2.pdf', '2.pdf', 'D:\\PrintCmpFile\\001\\2024\\0403\\16-21-22\\zhangsan\\result', 1);
INSERT INTO `check_diff_pdf` VALUES (23, 'zhangsan', '2024-04-05 12:45:10', '006', 'D:\\PrintCmpFile\\001\\2024\\0405\\12-45-10\\zhangsan\\5.pdf', '5.pdf', 'D:\\PrintCmpFile\\001\\2024\\0405\\12-45-10\\zhangsan\\6.pdf', '6.pdf', 'D:\\PrintCmpFile\\001\\2024\\0405\\12-45-10\\zhangsan\\result', 1);
INSERT INTO `check_diff_pdf` VALUES (24, 'zhangsan', '2024-04-05 12:47:43', '006', 'D:\\PrintCmpFile\\001\\2024\\0405\\12-47-41\\zhangsan\\3.pdf', '3.pdf', 'D:\\PrintCmpFile\\001\\2024\\0405\\12-47-41\\zhangsan\\4.pdf', '4.pdf', 'D:\\PrintCmpFile\\001\\2024\\0405\\12-47-41\\zhangsan\\result', 1);
INSERT INTO `check_diff_pdf` VALUES (25, 'zhangsan', '2024-04-07 19:36:26', '006', 'D:\\PrintCmpFile\\005\\2024\\0407\\19-36-25\\zhangsan\\a.pdf', 'a.pdf', 'D:\\PrintCmpFile\\005\\2024\\0407\\19-36-25\\zhangsan\\b.pdf', 'b.pdf', 'D:\\PrintCmpFile\\005\\2024\\0407\\19-36-25\\zhangsan\\result', 1);
INSERT INTO `check_diff_pdf` VALUES (26, 'zhangsan', '2024-04-08 19:12:19', '005', 'D:\\PrintCmpFile\\005\\2024\\0408\\19-12-19\\zhangsan\\3.pdf.pdf', '3.pdf.pdf', 'D:\\PrintCmpFile\\005\\2024\\0408\\19-12-19\\zhangsan\\4.pdf.pdf', '4.pdf.pdf', 'D:\\PrintCmpFile\\005\\2024\\0408\\19-12-19\\zhangsan\\result', 1);
INSERT INTO `check_diff_pdf` VALUES (27, 'zhangsan', '2024-04-08 19:22:37', '005', 'D:\\PrintCmpFile\\005\\2024\\0408\\19-22-36\\zhangsan\\3.pdf.pdf', '3.pdf.pdf', 'D:\\PrintCmpFile\\005\\2024\\0408\\19-22-36\\zhangsan\\4.pdf.pdf', '4.pdf.pdf', 'D:\\PrintCmpFile\\005\\2024\\0408\\19-22-36\\zhangsan\\result', 1);

-- ----------------------------
-- Table structure for check_language
-- ----------------------------
DROP TABLE IF EXISTS `check_language`;
CREATE TABLE `check_language`  (
  `id` int(11) NOT NULL AUTO_INCREMENT,
  `username` varchar(255) CHARACTER SET utf8 COLLATE utf8_general_ci NULL DEFAULT NULL,
  `dataline` datetime NULL DEFAULT NULL,
  `work_num` text CHARACTER SET utf8 COLLATE utf8_general_ci NULL,
  `pdf_path` text CHARACTER SET utf8 COLLATE utf8_general_ci NULL,
  `pdf_name` text CHARACTER SET utf8 COLLATE utf8_general_ci NULL,
  `result` text CHARACTER SET utf8 COLLATE utf8_general_ci NULL,
  `is_error` tinyint(255) NULL DEFAULT NULL,
  PRIMARY KEY (`id`) USING BTREE
) ENGINE = InnoDB AUTO_INCREMENT = 22 CHARACTER SET = utf8 COLLATE = utf8_general_ci ROW_FORMAT = Compact;

-- ----------------------------
-- Records of check_language
-- ----------------------------
INSERT INTO `check_language` VALUES (9, 'zhangsan', '2024-04-02 12:53:08', '008', 'D:\\PrintCmpFile\\008\\2024\\0402\\12-53-01\\zhangsan\\lang_cw.pdf', 'lang_cw.pdf', 'D:\\PrintCmpFile\\008\\2024\\0402\\12-53-01\\zhangsan\\result', 1);
INSERT INTO `check_language` VALUES (10, 'zhangsan', '2024-04-02 12:54:42', '008', 'D:\\PrintCmpFile\\008\\2024\\0402\\12-54-35\\zhangsan\\lang.pdf', 'lang.pdf', 'D:\\PrintCmpFile\\008\\2024\\0402\\12-54-35\\zhangsan\\result', 1);
INSERT INTO `check_language` VALUES (11, 'zhangsan', '2024-04-03 16:19:31', '008', 'D:\\PrintCmpFile\\001\\2024\\0403\\16-19-31\\zhangsan\\lang.pdf', 'lang.pdf', 'D:\\PrintCmpFile\\001\\2024\\0403\\16-19-31\\zhangsan\\result', 1);
INSERT INTO `check_language` VALUES (12, 'zhangsan', '2024-04-07 19:38:10', '008', 'D:\\PrintCmpFile\\003\\2024\\0407\\19-38-10\\zhangsan\\a.pdf', 'a.pdf', 'D:\\PrintCmpFile\\003\\2024\\0407\\19-38-10\\zhangsan\\result', 1);
INSERT INTO `check_language` VALUES (13, 'zhangsan', '2024-04-07 19:58:52', '008', 'D:\\PrintCmpFile\\003\\2024\\0407\\19-58-52\\zhangsan\\a.pdf', 'a.pdf', 'D:\\PrintCmpFile\\003\\2024\\0407\\19-58-52\\zhangsan\\result', 1);
INSERT INTO `check_language` VALUES (14, 'zhangsan', '2024-04-07 22:22:00', '008', 'D:\\PrintCmpFile\\003\\2024\\0407\\22-22-00\\zhangsan\\a.pdf', 'a.pdf', 'D:\\PrintCmpFile\\003\\2024\\0407\\22-22-00\\zhangsan\\result', 1);
INSERT INTO `check_language` VALUES (15, 'zhangsan', '2024-04-07 22:23:19', '008', 'D:\\PrintCmpFile\\003\\2024\\0407\\22-23-19\\zhangsan\\a.pdf', 'a.pdf', 'D:\\PrintCmpFile\\003\\2024\\0407\\22-23-19\\zhangsan\\result', 1);
INSERT INTO `check_language` VALUES (16, 'zhangsan', '2024-04-07 22:24:39', '008', 'D:\\PrintCmpFile\\003\\2024\\0407\\22-24-39\\zhangsan\\a.pdf', 'a.pdf', 'D:\\PrintCmpFile\\003\\2024\\0407\\22-24-39\\zhangsan\\result', 1);
INSERT INTO `check_language` VALUES (17, 'zhangsan', '2024-04-07 22:32:06', '008', 'D:\\PrintCmpFile\\003\\2024\\0407\\22-32-06\\zhangsan\\a.pdf', 'a.pdf', 'D:\\PrintCmpFile\\003\\2024\\0407\\22-32-06\\zhangsan\\result', 1);
INSERT INTO `check_language` VALUES (18, 'zhangsan', '2024-04-08 14:31:22', '003', 'D:\\PrintCmpFile\\003\\2024\\0408\\14-31-22\\zhangsan\\a.pdf', 'a.pdf', 'D:\\PrintCmpFile\\003\\2024\\0408\\14-31-22\\zhangsan\\result', 1);
INSERT INTO `check_language` VALUES (19, 'zhangsan', '2024-04-08 15:19:36', '003', 'D:\\PrintCmpFile\\003\\2024\\0408\\15-19-36\\zhangsan\\1.pdf.pdf', '1.pdf.pdf', 'D:\\PrintCmpFile\\003\\2024\\0408\\15-19-36\\zhangsan\\result', 1);
INSERT INTO `check_language` VALUES (20, 'zhangsan', '2024-04-08 19:22:09', '003', 'D:\\PrintCmpFile\\003\\2024\\0408\\19-22-09\\zhangsan\\1.pdf.pdf', '1.pdf.pdf', 'D:\\PrintCmpFile\\003\\2024\\0408\\19-22-09\\zhangsan\\result', 1);
INSERT INTO `check_language` VALUES (21, 'zhangsan', '2024-04-10 09:27:03', '003', 'D:\\PrintCmpFile\\003\\2024\\0410\\09-27-03\\zhangsan\\1.pdf', '1.pdf', 'D:\\PrintCmpFile\\003\\2024\\0410\\09-27-03\\zhangsan\\result', 1);

-- ----------------------------
-- Table structure for check_pagenumber
-- ----------------------------
DROP TABLE IF EXISTS `check_pagenumber`;
CREATE TABLE `check_pagenumber`  (
  `id` int(11) NOT NULL AUTO_INCREMENT,
  `username` varchar(255) CHARACTER SET utf8 COLLATE utf8_general_ci NULL DEFAULT NULL,
  `dataline` datetime NULL DEFAULT NULL,
  `work_num` text CHARACTER SET utf8 COLLATE utf8_general_ci NULL,
  `pdf_path` text CHARACTER SET utf8 COLLATE utf8_general_ci NULL,
  `pdf_name` text CHARACTER SET utf8 COLLATE utf8_general_ci NULL,
  `result` text CHARACTER SET utf8 COLLATE utf8_general_ci NULL,
  `is_error` tinyint(255) NULL DEFAULT NULL,
  PRIMARY KEY (`id`) USING BTREE
) ENGINE = InnoDB AUTO_INCREMENT = 45 CHARACTER SET = utf8 COLLATE = utf8_general_ci ROW_FORMAT = Compact;

-- ----------------------------
-- Records of check_pagenumber
-- ----------------------------
INSERT INTO `check_pagenumber` VALUES (1, 'zhangsan', '2024-03-29 13:17:36', '006', 'D:\\PrintCmpFile\\006\\2024\\0329\\13-17-34\\zhangsan\\cw.pdf', 'cw.pdf', 'D:\\PrintCmpFile\\006\\2024\\0329\\13-17-34\\zhangsan\\result', 1);
INSERT INTO `check_pagenumber` VALUES (2, 'zhangsan', '2024-03-29 22:48:24', '006', 'D:\\PrintCmpFile\\006\\2024\\0329\\22-48-23\\zhangsan\\cw.pdf', 'cw.pdf', 'D:\\PrintCmpFile\\006\\2024\\0329\\22-48-23\\zhangsan\\result', 1);
INSERT INTO `check_pagenumber` VALUES (3, 'zhangsan', '2024-03-29 22:49:50', '006', 'D:\\PrintCmpFile\\006\\2024\\0329\\22-49-35\\zhangsan\\1.pdf', '1.pdf', 'D:\\PrintCmpFile\\006\\2024\\0329\\22-49-35\\zhangsan\\result', 0);
INSERT INTO `check_pagenumber` VALUES (4, 'zhangsan', '2024-03-29 22:54:21', '006', 'D:\\PrintCmpFile\\006\\2024\\0329\\22-54-20\\zhangsan\\1.pdf', '1.pdf', 'D:\\PrintCmpFile\\006\\2024\\0329\\22-54-20\\zhangsan\\result', 0);
INSERT INTO `check_pagenumber` VALUES (5, 'zhangsan', '2024-03-30 13:58:54', '006', 'D:\\PrintCmpFile\\006\\2024\\0330\\13-58-53\\zhangsan\\1.pdf', '1.pdf', 'D:\\PrintCmpFile\\006\\2024\\0330\\13-58-53\\zhangsan\\result', 0);
INSERT INTO `check_pagenumber` VALUES (6, 'zhangsan', '2024-03-30 14:01:39', '006', 'D:\\PrintCmpFile\\006\\2024\\0330\\14-01-38\\zhangsan\\1.pdf', '1.pdf', 'D:\\PrintCmpFile\\006\\2024\\0330\\14-01-38\\zhangsan\\result', 0);
INSERT INTO `check_pagenumber` VALUES (7, 'zhangsan', '2024-04-02 12:41:34', '006', 'D:\\PrintCmpFile\\004\\2024\\0402\\12-41-33\\zhangsan\\1.pdf', '1.pdf', 'D:\\PrintCmpFile\\004\\2024\\0402\\12-41-33\\zhangsan\\result', 0);
INSERT INTO `check_pagenumber` VALUES (8, 'zhangsan', '2024-04-02 12:43:57', '006', 'D:\\PrintCmpFile\\004\\2024\\0402\\12-43-55\\zhangsan\\num_cw.pdf', 'num_cw.pdf', 'D:\\PrintCmpFile\\004\\2024\\0402\\12-43-55\\zhangsan\\result', 1);
INSERT INTO `check_pagenumber` VALUES (9, 'zhangsan', '2024-04-02 12:50:18', '008', 'D:\\PrintCmpFile\\004\\2024\\0402\\12-50-11\\zhangsan\\lang_cw.pdf', 'lang_cw.pdf', 'D:\\PrintCmpFile\\004\\2024\\0402\\12-50-11\\zhangsan\\result', 1);
INSERT INTO `check_pagenumber` VALUES (10, 'zhangsan', '2024-04-03 16:17:33', '006', 'D:\\PrintCmpFile\\001\\2024\\0403\\16-17-33\\zhangsan\\num_cw.pdf', 'num_cw.pdf', 'D:\\PrintCmpFile\\001\\2024\\0403\\16-17-33\\zhangsan\\result', 1);
INSERT INTO `check_pagenumber` VALUES (11, 'zhangsan', '2024-04-03 16:19:04', '006', 'D:\\PrintCmpFile\\001\\2024\\0403\\16-19-04\\zhangsan\\num_cw.pdf', 'num_cw.pdf', 'D:\\PrintCmpFile\\001\\2024\\0403\\16-19-04\\zhangsan\\result', 1);
INSERT INTO `check_pagenumber` VALUES (12, 'zhangsan', '2024-04-07 10:46:44', '006', 'D:\\PrintCmpFile\\002\\2024\\0407\\10-46-44\\zhangsan\\num_cw.pdf', 'num_cw.pdf', 'D:\\PrintCmpFile\\002\\2024\\0407\\10-46-44\\zhangsan\\result', 1);
INSERT INTO `check_pagenumber` VALUES (13, 'zhangsan', '2024-04-07 19:39:26', '006', 'D:\\PrintCmpFile\\002\\2024\\0407\\19-39-26\\zhangsan\\a.pdf', 'a.pdf', 'D:\\PrintCmpFile\\002\\2024\\0407\\19-39-26\\zhangsan\\result', 1);
INSERT INTO `check_pagenumber` VALUES (14, 'zhangsan', '2024-04-08 09:49:06', '006', 'D:\\PrintCmpFile\\002\\2024\\0408\\09-49-06\\zhangsan\\a.pdf', 'a.pdf', 'D:\\PrintCmpFile\\002\\2024\\0408\\09-49-06\\zhangsan\\result', 1);
INSERT INTO `check_pagenumber` VALUES (15, 'zhangsan', '2024-04-08 10:07:59', '006', 'D:\\PrintCmpFile\\002\\2024\\0408\\10-07-59\\zhangsan\\a.pdf', 'a.pdf', 'D:\\PrintCmpFile\\002\\2024\\0408\\10-07-59\\zhangsan\\result', 1);
INSERT INTO `check_pagenumber` VALUES (16, 'zhangsan', '2024-04-08 10:09:28', '006', 'D:\\PrintCmpFile\\002\\2024\\0408\\10-09-28\\zhangsan\\a.pdf', 'a.pdf', 'D:\\PrintCmpFile\\002\\2024\\0408\\10-09-28\\zhangsan\\result', 1);
INSERT INTO `check_pagenumber` VALUES (17, 'zhangsan', '2024-04-08 10:10:15', '006', 'D:\\PrintCmpFile\\002\\2024\\0408\\10-10-15\\zhangsan\\a.pdf', 'a.pdf', 'D:\\PrintCmpFile\\002\\2024\\0408\\10-10-15\\zhangsan\\result', 0);
INSERT INTO `check_pagenumber` VALUES (18, 'zhangsan', '2024-04-08 10:11:19', '006', 'D:\\PrintCmpFile\\002\\2024\\0408\\10-11-19\\zhangsan\\a.pdf', 'a.pdf', 'D:\\PrintCmpFile\\002\\2024\\0408\\10-11-19\\zhangsan\\result', 0);
INSERT INTO `check_pagenumber` VALUES (19, 'zhangsan', '2024-04-08 10:12:29', '006', 'D:\\PrintCmpFile\\002\\2024\\0408\\10-12-29\\zhangsan\\a.pdf', 'a.pdf', 'D:\\PrintCmpFile\\002\\2024\\0408\\10-12-29\\zhangsan\\result', 0);
INSERT INTO `check_pagenumber` VALUES (20, 'zhangsan', '2024-04-08 10:21:33', '006', 'D:\\PrintCmpFile\\002\\2024\\0408\\10-21-33\\zhangsan\\a.pdf', 'a.pdf', 'D:\\PrintCmpFile\\002\\2024\\0408\\10-21-33\\zhangsan\\result', 0);
INSERT INTO `check_pagenumber` VALUES (21, 'zhangsan', '2024-04-08 10:22:20', '006', 'D:\\PrintCmpFile\\002\\2024\\0408\\10-22-20\\zhangsan\\a.pdf', 'a.pdf', 'D:\\PrintCmpFile\\002\\2024\\0408\\10-22-20\\zhangsan\\result', 1);
INSERT INTO `check_pagenumber` VALUES (22, 'zhangsan', '2024-04-08 10:23:44', '006', 'D:\\PrintCmpFile\\002\\2024\\0408\\10-23-44\\zhangsan\\a.pdf', 'a.pdf', 'D:\\PrintCmpFile\\002\\2024\\0408\\10-23-44\\zhangsan\\result', 0);
INSERT INTO `check_pagenumber` VALUES (23, 'zhangsan', '2024-04-08 10:24:10', '006', 'D:\\PrintCmpFile\\002\\2024\\0408\\10-24-10\\zhangsan\\a.pdf', 'a.pdf', 'D:\\PrintCmpFile\\002\\2024\\0408\\10-24-10\\zhangsan\\result', 1);
INSERT INTO `check_pagenumber` VALUES (24, 'zhangsan', '2024-04-08 10:24:29', '006', 'D:\\PrintCmpFile\\002\\2024\\0408\\10-24-29\\zhangsan\\a.pdf', 'a.pdf', 'D:\\PrintCmpFile\\002\\2024\\0408\\10-24-29\\zhangsan\\result', 0);
INSERT INTO `check_pagenumber` VALUES (25, 'zhangsan', '2024-04-08 10:30:01', '006', 'D:\\PrintCmpFile\\002\\2024\\0408\\10-30-01\\zhangsan\\a.pdf', 'a.pdf', 'D:\\PrintCmpFile\\002\\2024\\0408\\10-30-01\\zhangsan\\result', 1);
INSERT INTO `check_pagenumber` VALUES (26, 'zhangsan', '2024-04-08 10:30:43', '006', 'D:\\PrintCmpFile\\002\\2024\\0408\\10-30-43\\zhangsan\\a.pdf', 'a.pdf', 'D:\\PrintCmpFile\\002\\2024\\0408\\10-30-43\\zhangsan\\result', 1);
INSERT INTO `check_pagenumber` VALUES (27, 'zhangsan', '2024-04-08 10:31:26', '006', 'D:\\PrintCmpFile\\002\\2024\\0408\\10-31-26\\zhangsan\\a.pdf', 'a.pdf', 'D:\\PrintCmpFile\\002\\2024\\0408\\10-31-26\\zhangsan\\result', 1);
INSERT INTO `check_pagenumber` VALUES (28, 'zhangsan', '2024-04-08 10:34:33', '006', 'D:\\PrintCmpFile\\002\\2024\\0408\\10-34-32\\zhangsan\\a.pdf', 'a.pdf', 'D:\\PrintCmpFile\\002\\2024\\0408\\10-34-32\\zhangsan\\result', 1);
INSERT INTO `check_pagenumber` VALUES (29, 'zhangsan', '2024-04-08 10:35:05', '006', 'D:\\PrintCmpFile\\002\\2024\\0408\\10-35-05\\zhangsan\\a.pdf', 'a.pdf', 'D:\\PrintCmpFile\\002\\2024\\0408\\10-35-05\\zhangsan\\result', 1);
INSERT INTO `check_pagenumber` VALUES (30, 'zhangsan', '2024-04-08 10:35:32', '006', 'D:\\PrintCmpFile\\002\\2024\\0408\\10-35-32\\zhangsan\\a.pdf', 'a.pdf', 'D:\\PrintCmpFile\\002\\2024\\0408\\10-35-32\\zhangsan\\result', 1);
INSERT INTO `check_pagenumber` VALUES (31, 'zhangsan', '2024-04-08 10:38:41', '006', 'D:\\PrintCmpFile\\002\\2024\\0408\\10-38-41\\zhangsan\\a.pdf', 'a.pdf', 'D:\\PrintCmpFile\\002\\2024\\0408\\10-38-41\\zhangsan\\result', 1);
INSERT INTO `check_pagenumber` VALUES (32, 'zhangsan', '2024-04-08 12:48:07', '006', 'D:\\PrintCmpFile\\002\\2024\\0408\\12-48-07\\zhangsan\\a.pdf', 'a.pdf', 'D:\\PrintCmpFile\\002\\2024\\0408\\12-48-07\\zhangsan\\result', 1);
INSERT INTO `check_pagenumber` VALUES (33, 'zhangsan', '2024-04-08 12:50:58', '006', 'D:\\PrintCmpFile\\002\\2024\\0408\\12-50-58\\zhangsan\\1.pdf', '1.pdf', 'D:\\PrintCmpFile\\002\\2024\\0408\\12-50-58\\zhangsan\\result', 1);
INSERT INTO `check_pagenumber` VALUES (34, 'zhangsan', '2024-04-08 12:54:15', '006', 'D:\\PrintCmpFile\\002\\2024\\0408\\12-54-15\\zhangsan\\1.pdf', '1.pdf', 'D:\\PrintCmpFile\\002\\2024\\0408\\12-54-15\\zhangsan\\result', 1);
INSERT INTO `check_pagenumber` VALUES (35, 'zhangsan', '2024-04-08 12:59:40', '002', 'D:\\PrintCmpFile\\002\\2024\\0408\\12-59-40\\zhangsan\\1.pdf', '1.pdf', 'D:\\PrintCmpFile\\002\\2024\\0408\\12-59-40\\zhangsan\\result', 1);
INSERT INTO `check_pagenumber` VALUES (36, 'zhangsan', '2024-04-08 14:18:09', '002', 'D:\\PrintCmpFile\\002\\2024\\0408\\14-18-09\\zhangsan\\cw.pdf.pdf', 'cw.pdf.pdf', 'D:\\PrintCmpFile\\002\\2024\\0408\\14-18-09\\zhangsan\\result', 1);
INSERT INTO `check_pagenumber` VALUES (37, 'zhangsan', '2024-04-08 19:20:54', '002', 'D:\\PrintCmpFile\\002\\2024\\0408\\19-20-54\\zhangsan\\cw.pdf.pdf', 'cw.pdf.pdf', 'D:\\PrintCmpFile\\002\\2024\\0408\\19-20-54\\zhangsan\\result', 1);
INSERT INTO `check_pagenumber` VALUES (38, 'zhangsan', '2024-04-10 08:45:23', '002', 'D:\\PrintCmpFile\\002\\2024\\0410\\08-45-23\\zhangsan\\cw.pdf.pdf', 'cw.pdf.pdf', 'D:\\PrintCmpFile\\002\\2024\\0410\\08-45-23\\zhangsan\\result', 1);
INSERT INTO `check_pagenumber` VALUES (39, 'zhangsan', '2024-04-10 09:08:24', '002', 'D:\\PrintCmpFile\\002\\2024\\0410\\09-08-24\\zhangsan\\cw.pdf.pdf', 'cw.pdf.pdf', 'D:\\PrintCmpFile\\002\\2024\\0410\\09-08-24\\zhangsan\\result', 1);
INSERT INTO `check_pagenumber` VALUES (40, 'zhangsan', '2024-04-10 09:25:33', '002', 'D:\\PrintCmpFile\\002\\2024\\0410\\09-25-33\\zhangsan\\cw.pdf', 'cw.pdf', 'D:\\PrintCmpFile\\002\\2024\\0410\\09-25-33\\zhangsan\\result', 1);
INSERT INTO `check_pagenumber` VALUES (41, 'zhangsan', '2024-04-10 13:24:15', '002', 'D:\\PrintCmpFile\\002\\2024\\0410\\13-24-14\\zhangsan\\cw.pdf', 'cw.pdf', 'D:\\PrintCmpFile\\002\\2024\\0410\\13-24-14\\zhangsan\\result', 1);
INSERT INTO `check_pagenumber` VALUES (42, 'zhangsan', '2024-04-10 13:26:10', '002', 'D:\\PrintCmpFile\\002\\2024\\0410\\13-26-10\\zhangsan\\cw.pdf', 'cw.pdf', 'D:\\PrintCmpFile\\002\\2024\\0410\\13-26-10\\zhangsan\\result', 1);
INSERT INTO `check_pagenumber` VALUES (43, 'zhangsan', '2024-04-10 13:32:38', '002', 'D:\\PrintCmpFile\\002\\2024\\0410\\13-32-38\\zhangsan\\cw.pdf', 'cw.pdf', 'D:\\PrintCmpFile\\002\\2024\\0410\\13-32-38\\zhangsan\\result', 1);
INSERT INTO `check_pagenumber` VALUES (44, 'zhangsan', '2024-04-10 13:52:26', '002', 'D:\\PrintCmpFile\\002\\2024\\0410\\13-52-26\\zhangsan\\cw.pdf', 'cw.pdf', 'D:\\PrintCmpFile\\002\\2024\\0410\\13-52-26\\zhangsan\\result', 1);

-- ----------------------------
-- Table structure for check_screw
-- ----------------------------
DROP TABLE IF EXISTS `check_screw`;
CREATE TABLE `check_screw`  (
  `id` int(11) NOT NULL AUTO_INCREMENT,
  `username` varchar(255) CHARACTER SET utf8 COLLATE utf8_general_ci NULL DEFAULT NULL,
  `dataline` datetime NULL DEFAULT NULL,
  `work_num` text CHARACTER SET utf8 COLLATE utf8_general_ci NULL,
  `pdf_path` text CHARACTER SET utf8 COLLATE utf8_general_ci NULL,
  `pdf_name` text CHARACTER SET utf8 COLLATE utf8_general_ci NULL,
  `result` text CHARACTER SET utf8 COLLATE utf8_general_ci NULL,
  `is_error` tinyint(255) NULL DEFAULT NULL,
  PRIMARY KEY (`id`) USING BTREE
) ENGINE = InnoDB AUTO_INCREMENT = 19 CHARACTER SET = utf8 COLLATE = utf8_general_ci ROW_FORMAT = Compact;

-- ----------------------------
-- Records of check_screw
-- ----------------------------
INSERT INTO `check_screw` VALUES (4, 'zhangsan', '2024-03-31 11:18:12', '004', 'D:\\PrintCmpFile\\004\\2024\\0331\\11-17-36\\zhangsan\\1.pdf', '1.pdf', 'D:\\PrintCmpFile\\004\\2024\\0331\\11-17-36\\zhangsan\\result', 1);
INSERT INTO `check_screw` VALUES (5, 'zhangsan', '2024-04-02 12:58:33', '004', 'D:\\PrintCmpFile\\008\\2024\\0402\\12-57-55\\zhangsan\\Screw.pdf', 'Screw.pdf', 'D:\\PrintCmpFile\\008\\2024\\0402\\12-57-55\\zhangsan\\result', 1);
INSERT INTO `check_screw` VALUES (6, 'zhangsan', '2024-04-02 13:10:02', '004', 'D:\\PrintCmpFile\\004\\2024\\0402\\13-09-25\\zhangsan\\Screw.pdf', 'Screw.pdf', 'D:\\PrintCmpFile\\004\\2024\\0402\\13-09-25\\zhangsan\\result', 1);
INSERT INTO `check_screw` VALUES (7, 'zhangsan', '2024-04-02 13:14:29', '004', 'D:\\PrintCmpFile\\004\\2024\\0402\\13-13-52\\zhangsan\\Screw_dui.pdf', 'Screw_dui.pdf', 'D:\\PrintCmpFile\\004\\2024\\0402\\13-13-52\\zhangsan\\result', 1);
INSERT INTO `check_screw` VALUES (8, 'zhangsan', '2024-04-02 13:16:18', '004', 'D:\\PrintCmpFile\\004\\2024\\0402\\13-15-41\\zhangsan\\Screw_dui.pdf', 'Screw_dui.pdf', 'D:\\PrintCmpFile\\004\\2024\\0402\\13-15-41\\zhangsan\\result', 1);
INSERT INTO `check_screw` VALUES (9, 'zhangsan', '2024-04-02 13:21:57', '004', 'D:\\PrintCmpFile\\004\\2024\\0402\\13-21-19\\zhangsan\\Screw_dui.pdf', 'Screw_dui.pdf', 'D:\\PrintCmpFile\\004\\2024\\0402\\13-21-19\\zhangsan\\result', 1);
INSERT INTO `check_screw` VALUES (10, 'zhangsan', '2024-04-02 15:22:42', '004', 'D:\\PrintCmpFile\\004\\2024\\0402\\15-22-14\\zhangsan\\Screw_dui.pdf', 'Screw_dui.pdf', 'D:\\PrintCmpFile\\004\\2024\\0402\\15-22-14\\zhangsan\\result', 1);
INSERT INTO `check_screw` VALUES (11, 'zhangsan', '2024-04-02 15:24:54', '004', 'D:\\PrintCmpFile\\004\\2024\\0402\\15-24-27\\zhangsan\\Screw_dui.pdf', 'Screw_dui.pdf', 'D:\\PrintCmpFile\\004\\2024\\0402\\15-24-27\\zhangsan\\result', 1);
INSERT INTO `check_screw` VALUES (12, 'zhangsan', '2024-04-02 15:29:47', '004', 'D:\\PrintCmpFile\\004\\2024\\0402\\15-29-17\\zhangsan\\Screw_dui.pdf', 'Screw_dui.pdf', 'D:\\PrintCmpFile\\004\\2024\\0402\\15-29-17\\zhangsan\\result', 0);
INSERT INTO `check_screw` VALUES (13, 'zhangsan', '2024-04-03 16:21:59', '004', 'D:\\PrintCmpFile\\001\\2024\\0403\\16-21-59\\zhangsan\\Screw_dui.pdf', 'Screw_dui.pdf', 'D:\\PrintCmpFile\\001\\2024\\0403\\16-21-59\\zhangsan\\result', 0);
INSERT INTO `check_screw` VALUES (14, 'zhangsan', '2024-04-07 19:40:54', '004', 'D:\\PrintCmpFile\\001\\2024\\0407\\19-40-54\\zhangsan\\a.pdf', 'a.pdf', 'D:\\PrintCmpFile\\001\\2024\\0407\\19-40-54\\zhangsan\\result', 0);
INSERT INTO `check_screw` VALUES (15, 'zhangsan', '2024-04-08 14:46:11', '001', 'D:\\PrintCmpFile\\001\\2024\\0408\\14-46-11\\zhangsan\\a.pdf', 'a.pdf', 'D:\\PrintCmpFile\\001\\2024\\0408\\14-46-11\\zhangsan\\result', 0);
INSERT INTO `check_screw` VALUES (16, 'zhangsan', '2024-04-08 15:24:22', '001', 'D:\\PrintCmpFile\\001\\2024\\0408\\15-24-22\\zhangsan\\1.pdf.pdf', '1.pdf.pdf', 'D:\\PrintCmpFile\\001\\2024\\0408\\15-24-22\\zhangsan\\result', 0);
INSERT INTO `check_screw` VALUES (17, 'zhangsan', '2024-04-08 19:21:48', '001', 'D:\\PrintCmpFile\\001\\2024\\0408\\19-21-48\\zhangsan\\1.pdf.pdf', '1.pdf.pdf', 'D:\\PrintCmpFile\\001\\2024\\0408\\19-21-48\\zhangsan\\result', 0);
INSERT INTO `check_screw` VALUES (18, 'zhangsan', '2024-04-10 09:26:29', '001', 'D:\\PrintCmpFile\\001\\2024\\0410\\09-26-29\\zhangsan\\1.pdf', '1.pdf', 'D:\\PrintCmpFile\\001\\2024\\0410\\09-26-29\\zhangsan\\result', 0);

-- ----------------------------
-- Table structure for functionalist
-- ----------------------------
DROP TABLE IF EXISTS `functionalist`;
CREATE TABLE `functionalist`  (
  `Id` int(11) NOT NULL AUTO_INCREMENT,
  `功能编码` varchar(255) CHARACTER SET utf8 COLLATE utf8_general_ci NOT NULL,
  `功能名称` varchar(255) CHARACTER SET utf8 COLLATE utf8_general_ci NOT NULL,
  `功能描述` text CHARACTER SET utf8 COLLATE utf8_general_ci NULL,
  `备注` text CHARACTER SET utf8 COLLATE utf8_general_ci NULL,
  PRIMARY KEY (`Id`) USING BTREE,
  UNIQUE INDEX `功能编码`(`功能编码`) USING BTREE
) ENGINE = InnoDB AUTO_INCREMENT = 11 CHARACTER SET = utf8 COLLATE = utf8_general_ci ROW_FORMAT = Compact;

-- ----------------------------
-- Records of functionalist
-- ----------------------------
INSERT INTO `functionalist` VALUES (1, '001', 'CE对比', '将两个CE图表进行对比', '备注内容');
INSERT INTO `functionalist` VALUES (2, '002', '爆炸图对比', '将数据导出到CSV文件', '备注内容');
INSERT INTO `functionalist` VALUES (3, '003', '零件计数', '导出特定计数数据', '备注内容');
INSERT INTO `functionalist` VALUES (4, '004', '螺丝包', '根据用户账单生成报告', '备注内容');
INSERT INTO `functionalist` VALUES (5, '005', '明细表对比', '对比两个明细表中的不同', '备注内容');
INSERT INTO `functionalist` VALUES (6, '006', '页码检查', '生成财务总表', '备注内容');
INSERT INTO `functionalist` VALUES (7, '007', '贴纸尺寸', '生成收款尾页报告', '备注内容');
INSERT INTO `functionalist` VALUES (8, '008', '语言顺序', '删除系统中不必要的语言文件', '备注内容');
INSERT INTO `functionalist` VALUES (9, '009', '文件对比', '比较两个文件的差异', '备注内容');
INSERT INTO `functionalist` VALUES (10, '010', '实物检测', '确认实物与系统数据一致', '备注内容');

-- ----------------------------
-- Table structure for user
-- ----------------------------
DROP TABLE IF EXISTS `user`;
CREATE TABLE `user`  (
  `username` varchar(255) CHARACTER SET utf8 COLLATE utf8_general_ci NOT NULL,
  `password` varchar(255) CHARACTER SET utf8 COLLATE utf8_general_ci NULL DEFAULT NULL
) ENGINE = InnoDB CHARACTER SET = utf8 COLLATE = utf8_general_ci ROW_FORMAT = Compact;

-- ----------------------------
-- Records of user
-- ----------------------------
INSERT INTO `user` VALUES ('zhangsan', '123');

SET FOREIGN_KEY_CHECKS = 1;
