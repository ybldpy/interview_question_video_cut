create table videoapp.t_user
(
    id       int(10) auto_increment
        primary key,
    password varchar(200) charset latin1 not null,
    username varchar(200) charset latin1 not null,
    constraint username
        unique (username)
)
    charset = utf8;

create table videoapp.t_video_process
(
    id        varchar(200) not null
        primary key,
    video_url varchar(200) not null,
    local_url varchar(200) null,
    ctime     bigint       not null,
    uid       int          not null
);
