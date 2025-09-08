create Table events (
    id Integer primary key generated autoincrement,
    title text not null,
    description text,
    location text,
    date text not null,
    price real not null
    image text,
);