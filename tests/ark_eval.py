"""
Script to evaluate captured arks on legacy n2t vs new n2t, arks, and ezid.


Notes:

ark prefixes:

```
select prefix, count(*) as n from pid where scheme='ark' group by prefix order by n asc;
```

Sample n arks from pid:
```
create macro test_cases(nsamples) as table
  select data.rn as rn, data.prefix as prefix, data.original as original from (
    select a.*, row_number() over (partition by a.prefix) as rn
      from (
          select distinct pid.prefix, pid.original from pids.pid
          where pid.scheme = 'ark' and length(pid.value) > 0
          order by pid.prefix, length(pid.original)
      ) a
  ) data
  where data.rn <= 1
  order by prefix asc, rn asc;
```

```
create macro test_cases(nsamples) as table
  select data.rn as rn, data.prefix as prefix, naans.who.name as name, data.original as original from (
    select a.*, row_number() over (partition by a.prefix) as rn
      from (
          select distinct pid.prefix, pid.original from pids.pid
          inner join ezid on pid.prefix=ezid.prefix
          where pid.scheme = 'ark'
          order by pid.prefix, length(pid.original)
      ) a
  ) data, naans
  where data.rn <= nsamples and data.prefix=naans.what
  order by prefix asc, rn asc;
```

Get a few non-ark identifiers from the less popular schemes
```
select original from pid where scheme in (
    select b.scheme from (
        select scheme, count(*) as n from pid  group by scheme
    ) as b where b.n < 3
);
```
"""