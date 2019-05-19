SET NAMES utf8;
SET time_zone = '+00:00';
SET foreign_key_checks = 0;
SET sql_mode = 'NO_AUTO_VALUE_ON_ZERO';

DROP TABLE IF EXISTS `bot_tipnotify_user`;
CREATE TABLE `bot_tipnotify_user` (
  `user_id` varchar(32) NOT NULL,
  `date` int(11) NOT NULL,
  KEY `user_id` (`user_id`)
) ENGINE=InnoDB DEFAULT CHARSET=ascii;


DROP TABLE IF EXISTS `dego_external_tx`;
CREATE TABLE `dego_external_tx` (
`user_id` varchar(32) NOT NULL,
`amount` bigint(20) NOT NULL,
`fee` int(11) NOT NULL,
`to_address` varchar(128) NOT NULL,
`paymentid` varchar(64) DEFAULT NULL,
`type` enum('SEND','WITHDRAW') NOT NULL,
`date` int(11) NOT NULL,
`tx_hash` varchar(64) NOT NULL,
KEY `user_id` (`user_id`)
) ENGINE=InnoDB DEFAULT CHARSET=ascii;


CREATE TABLE `dego_mv_tx` (
`from_userid` varchar(32) CHARACTER SET ascii NOT NULL,
`from_name` varchar(32) DEFAULT NULL,
`to_userid` varchar(32) CHARACTER SET ascii NOT NULL,
`to_name` varchar(32) DEFAULT NULL,
`server_id` varchar(32) CHARACTER SET ascii NOT NULL DEFAULT 'DM',
`server_name` varchar(32) NOT NULL DEFAULT 'DM',
`amount` bigint(20) NOT NULL,
`type` enum('TIP','TIPS','TIPALL','DONATE') CHARACTER SET ascii NOT NULL,
`date` int(11) NOT NULL,
KEY `from_userid` (`from_userid`),
KEY `to_userid` (`to_userid`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;


DROP TABLE IF EXISTS `dego_tag`;
CREATE TABLE `dego_tag` (
  `tag_id` varchar(32) CHARACTER SET utf8mb4 NOT NULL,
  `tag_desc` varchar(2048) CHARACTER SET utf8mb4 NOT NULL,
  `date_added` int(11) NOT NULL,
  `tag_serverid` varchar(32) NOT NULL,
  `added_byname` varchar(32) CHARACTER SET utf8mb4 NOT NULL,
  `added_byuid` varchar(32) NOT NULL,
  `num_trigger` int(11) NOT NULL DEFAULT '0',
  KEY `tag_id` (`tag_id`),
  KEY `tag_serverid` (`tag_serverid`)
) ENGINE=InnoDB DEFAULT CHARSET=ascii;


DROP TABLE IF EXISTS `dego_user`;
CREATE TABLE `dego_user` (
  `user_id` varchar(32) NOT NULL,
  `balance_wallet_address` varchar(128) NOT NULL,
  `user_wallet_address` varchar(128) DEFAULT NULL,
  `balance_wallet_address_ts` int(11) DEFAULT NULL,
  `balance_wallet_address_ch` int(11) DEFAULT NULL,
  `lastOptimize` int(11) DEFAULT NULL,
  `privateSpendKey` varchar(64) NOT NULL,
  UNIQUE KEY `user_id` (`user_id`),
  KEY `balance_wallet_address` (`balance_wallet_address`),
  KEY `user_wallet_address` (`user_wallet_address`)
) ENGINE=InnoDB DEFAULT CHARSET=ascii;


DROP TABLE IF EXISTS `dego_walletapi`;
CREATE TABLE `dego_walletapi` (
  `balance_wallet_address` varchar(128) NOT NULL,
  `actual_balance` bigint(20) NOT NULL DEFAULT '0',
  `locked_balance` bigint(20) NOT NULL DEFAULT '0',
  `lastUpdate` int(11) DEFAULT NULL,
  UNIQUE KEY `balance_wallet_address` (`balance_wallet_address`)
) ENGINE=InnoDB DEFAULT CHARSET=ascii;


DROP TABLE IF EXISTS `discord_messages`;
CREATE TABLE `discord_messages` (
`serverid` varchar(32) CHARACTER SET ascii NOT NULL,
`server_name` varchar(64) NOT NULL,
`channel_id` varchar(32) CHARACTER SET ascii NOT NULL,
`channel_name` varchar(64) NOT NULL,
`user_id` varchar(32) CHARACTER SET ascii NOT NULL,
`message_author` varchar(32) NOT NULL,
`message_id` varchar(32) CHARACTER SET ascii NOT NULL,
`message_time` int(11) NOT NULL,
UNIQUE KEY `message_id` (`message_id`),
KEY `message_time` (`message_time`),
KEY `serverid` (`serverid`),
KEY `channel_id` (`channel_id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;